"""
NeuroVynx: Quantitative EEG (qEEG) Engine
=========================================

This module computes standard quantitative metrics from EEG signals.
All metrics are gated by the Quality/Confidence engine to ensure 
that only reliable data is quantified.
"""

import numpy as np
from app.eeg.features import spectral

# --------------------------------------------------------------------------
# STANDARD BANDS & REGIONS
# --------------------------------------------------------------------------

BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 12.0),
    "beta": (12.0, 30.0)
}

REGION_MAPPING = {
    "Frontal": ["FP1", "FP2", "F3", "F4", "F7", "F8", "FZ", "FPZ"],
    "Central": ["C3", "C4", "CZ"],
    "Parietal": ["P3", "P4", "PZ"],
    "Occipital": ["O1", "O2", "OZ"],
    "Temporal": ["T3", "T7", "T4", "T8", "T5", "P7", "T6", "P8"]
}

CHANNEL_ALIASES = {
    "T3": "T7", "T7": "T3",
    "T4": "T8", "T8": "T4",
    "T5": "P7", "P7": "T5",
    "T6": "P8", "P8": "T6"
}

ASYMMETRY_PAIRS = [
    ("F3", "F4"),
    ("C3", "C4"),
    ("P3", "P4"),
    ("O1", "O2")
]

EPSILON = 1e-12 # Guard against log instability

def get_region_for_channel(channel_name: str) -> str:
    """Identifies region based on channel label and aliases."""
    channel_name = channel_name.upper().strip()
    for region, channels in REGION_MAPPING.items():
        if channel_name in channels:
            return region
        # Check aliases
        if channel_name in CHANNEL_ALIASES:
            if CHANNEL_ALIASES[channel_name] in channels:
                return region
    return "Unknown"

def compute_qeeg_layer(
    data_uv: np.ndarray,
    channels: list,
    sfreq: float,
    quality_info: dict,
    confidence_info: dict
):
    """
    Main entry point for qEEG feature extraction.
    Gated by Quality and Confidence.
    """
    results = {
        "is_available": False,
        "trust_level": "unavailable",
        "trust_reason": "No active EEG detected",
        "channel_metrics": [],
        "regional_metrics": [],
        "asymmetry_metrics": [],
        "summary": {},
        "warnings": []
    }

    # 1. CHANNEL ELIGIBILITY GATING
    # --------------------------------------------------------------------------
    eligible_indices = []
    eligible_names = []
    excluded_names = []
    
    per_channel_status = quality_info.get("per_channel_status", {})
    
    for i, ch in enumerate(channels):
        status = per_channel_status.get(ch, {})
        ch_type = status.get("type", "UNKNOWN")
        is_active = status.get("active", False)
        ch_quality = status.get("quality_score", 100) # Placeholder if not found
        
        # Determine eligibility
        # Rule: Only EEG channels, must be active, must NOT have fatal quality failures
        if ch_type == "EEG" and is_active and not status.get("is_fatal", False):
            # Hard threshold: Quality >= 40
            # Note: The quality_score for a channel might be 100 - (penalty * multiplier)
            # We'll use the final_score calculated in the engine if available, 
            # or reconstruct a basic check.
            
            # Since compute_segment_quality returns 0 for bad/warning in some cases, 
            # we check the 'status' directly from per_channel_status.
            if status.get("status") in ["good", "warning"]:
                eligible_indices.append(i)
                eligible_names.append(ch)
            else:
                excluded_names.append(ch)
        elif ch_type == "EEG":
            excluded_names.append(ch)

    if not eligible_indices:
        results["is_available"] = False
        results["trust_level"] = "unavailable"
        results["trust_reason"] = "insufficient_eeg_channels"
        results["reason"] = "Insufficient active EEG channels for qEEG analysis"
        return results

    # 2. COMPUTE PSD
    # --------------------------------------------------------------------------
    freqs, psd = spectral.compute_psd(data_uv[eligible_indices], sfreq)
    
    # 3. PER-CHANNEL FEATURES
    # --------------------------------------------------------------------------
    channel_data = {}
    for idx_in_psd, channel_idx in enumerate(eligible_indices):
        ch_name = channels[channel_idx]
        ch_psd = psd[idx_in_psd]
        
        abs_power = {}
        total_abs_power = 0.0
        
        for band, (low, high) in BANDS.items():
            power = spectral.band_power(ch_psd, freqs, (low, high))
            abs_power[band] = float(power)
            total_abs_power += power
            
        rel_power = {band: (p / (total_abs_power + EPSILON)) for band, p in abs_power.items()}
        dominant_band = max(rel_power, key=rel_power.get)
        
        # Determine Channel-Level Trust
        # Rule: Quality >= 70 AND Confidence >= 60 -> Trusted
        # We need the global confidence for this window as well.
        global_conf = quality_info.get("confidence_score", 0)
        ch_status = per_channel_status.get(ch_name, {})
        
        # We'll approximate a 'trusted' tag for the channel
        is_trusted = (ch_status.get("status") == "good") and (global_conf >= 60)
        trust_state = "trusted" if is_trusted else "borderline"
        
        channel_metrics = {
            "channel": ch_name,
            "region": get_region_for_channel(ch_name),
            "absolute_power": abs_power,
            "relative_power": rel_power,
            "dominant_band": dominant_band,
            "trust_level": trust_state,
            "units": "uV^2"
        }
        results["channel_metrics"].append(channel_metrics)
        channel_data[ch_name] = channel_metrics

    # 4. REGIONAL AGGREGATION
    # --------------------------------------------------------------------------
    regions_found = {}
    for ch_metric in results["channel_metrics"]:
        region = ch_metric["region"]
        if region == "Unknown": continue
        
        if region not in regions_found:
            regions_found[region] = {"abs": {b: [] for b in BANDS}, "rel": {b: [] for b in BANDS}, "count": 0}
        
        regions_found[region]["count"] += 1
        for b in BANDS:
            regions_found[region]["abs"][b].append(ch_metric["absolute_power"][b])
            regions_found[region]["rel"][b].append(ch_metric["relative_power"][b])

    for region, data in regions_found.items():
        regional_rel = {b: np.mean(data["rel"][b]) for b in BANDS}
        results["regional_metrics"].append({
            "region": region,
            "relative_power": regional_rel,
            "dominant_band": max(regional_rel, key=regional_rel.get),
            "channel_count": data["count"]
        })

    # 5. ASYMMETRY
    # --------------------------------------------------------------------------
    for left, right in ASYMMETRY_PAIRS:
        if left in channel_data and right in channel_data:
            # Both channels must be eligible
            pair_asym = {
                "pair": f"{left}-{right}",
                "bands": {}
            }
            
            for band in BANDS:
                p_left = channel_data[left]["absolute_power"][band]
                p_right = channel_data[right]["absolute_power"][band]
                
                # Formula: log(left + eps) - log(right + eps)
                log_asym = np.log(p_left + EPSILON) - np.log(p_right + EPSILON)
                
                pair_asym["bands"][band] = {
                    "log_asymmetry": float(log_asym),
                    "left_power": p_left,
                    "right_power": p_right,
                    "direction": "left_greater" if log_asym > 0 else "right_greater"
                }
            results["asymmetry_metrics"].append(pair_asym)

    # 6. GLOBAL SUMMARY & TRUST LEVEL
    # --------------------------------------------------------------------------
    win_quality = quality_info.get("eeg_quality_score", 0)
    win_conf = quality_info.get("confidence_score", 0)
    
    trust_level = "borderline"
    trust_reason = "stable_signal"
    
    if win_quality >= 70 and win_conf >= 60:
        trust_level = "trusted"
        trust_reason = "stable_signal"
    elif win_quality < 40:
        trust_level = "unavailable"
        trust_reason = "high_artifact_burden"
    else:
        # It's borderline
        if win_conf < 60:
            trust_reason = "low_interpretation_confidence"
        else:
            trust_reason = "modest_signal_quality"
        
    global_rel_powers = {b: np.mean([ch["relative_power"][b] for ch in results["channel_metrics"]]) for b in BANDS}
    
    results.update({
        "is_available": True,
        "trust_level": trust_level,
        "trust_reason": trust_reason,
        "eligible_eeg_channels": len(eligible_names),
        "excluded_eeg_channels": excluded_names,
        "summary": {
            "dominant_global_band": max(global_rel_powers, key=global_rel_powers.get),
            "global_relative_power": global_rel_powers
        }
    })

    return results
