"""
NeuroVynx: Quantitative EEG (qEEG) Engine
=========================================

This module computes standard quantitative metrics from EEG signals.
All metrics are gated by the Quality/Confidence engine to ensure 
that only reliable data is quantified.
"""

import numpy as np
from app.eeg.features import spectral
from app.eeg.config.analysis_standards import (
    CANONICAL_BANDS, TOTAL_POWER_RANGE, REGION_MAPPING, 
    CHANNEL_ALIASES, ASYMMETRY_PAIRS, EPSILON, 
    clean_name, get_region_for_channel
)
from app.eeg.qeeg import normative_gating



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
    
    for i, raw_ch in enumerate(channels):
        ch = clean_name(raw_ch)
        status = per_channel_status.get(raw_ch, {}) # Quality refers to raw EDF names
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
        raw_ch_name = channels[channel_idx]
        ch_name = clean_name(raw_ch_name)
        ch_psd = psd[idx_in_psd]
        
        abs_power = {}
        for band, (low, high) in CANONICAL_BANDS.items():
            power = spectral.band_power(ch_psd, freqs, (low, high))
            abs_power[band] = float(power)
            
        # Calculate per-channel relative power against the standard 0.5-30Hz denominator
        # This keeps the sub-band percentages consistent and meaningful locally.
        total_range_power = spectral.band_power(ch_psd, freqs, TOTAL_POWER_RANGE)
        rel_power = {band: (p / (total_range_power + EPSILON)) for band, p in abs_power.items()}
        dominant_band = max(rel_power, key=rel_power.get)
        
        # Determine Interpretation and Normative Eligibility (Phase 2)
        ch_status = per_channel_status.get(ch_name, {})
        ch_quality = ch_status.get("quality_score", 100) # Fallback to 100 if missing
        eligibility = normative_gating.assess_channel_eligibility(
            channel_name=ch_name,
            quality_score=ch_quality,
            has_reference=True # Future: Check against specific reference coverage
        )

        ch_metric = {
            "channel": ch_name,
            "region": get_region_for_channel(ch_name),
            "trust_level": ch_status.get("status", "unknown"),
            "quality_score": ch_quality,
            "absolute_power": abs_power,
            "relative_power": rel_power,
            "dominant_band": dominant_band,
            "eligibility": eligibility
        }
        results["channel_metrics"].append(ch_metric)
        channel_data[ch_name] = ch_metric
        
        # We'll approximate a 'trusted' tag for the channel
        global_conf = quality_info.get("confidence_score", 0)
        is_trusted = (ch_status.get("status") == "good") and (global_conf >= 60)
        trust_state = "trusted" if is_trusted else "borderline"
        ch_metric["trust_level"] = trust_state

    # 4. REGIONAL AGGREGATION
    # --------------------------------------------------------------------------
    regions_found = {}
    for ch_metric in results["channel_metrics"]:
        region = ch_metric["region"]
        if region == "Unknown": continue
        
        if region not in regions_found:
            regions_found[region] = {"abs": {b: [] for b in CANONICAL_BANDS}, "rel": {b: [] for b in CANONICAL_BANDS}, "count": 0}
        
        regions_found[region]["count"] += 1
        for b in CANONICAL_BANDS:
            regions_found[region]["abs"][b].append(ch_metric["absolute_power"][b])
            regions_found[region]["rel"][b].append(ch_metric["relative_power"][b])

    # Aggregating regional metrics
    interp_conf = quality_info.get("confidence_score", 1.0) / 100.0 if "confidence_score" in quality_info else 1.0

    for region, data in regions_found.items():
        # Safety: Ensure we don't pass empty lists to np.mean
        regional_rel = {}
        for b in CANONICAL_BANDS:
            vals = data["rel"][b]
            regional_rel[b] = float(np.mean(vals)) if vals else 0.0
            
        region_channels = [ch for ch in results["channel_metrics"] if ch["region"] == region]
        mean_quality = float(np.mean([ch["quality_score"] for ch in region_channels])) if region_channels else 0.0
        
        # Regional Gating (Phase 2)
        eligibility = normative_gating.assess_regional_eligibility(
            region_name=region,
            z_score=0.0, 
            trusted_channel_count=data["count"],
            mean_quality=mean_quality,
            interpretation_confidence=interp_conf
        )

        results["regional_metrics"].append({
            "region": region,
            "relative_power": regional_rel,
            "dominant_band": max(regional_rel, key=regional_rel.get),
            "channel_count": data["count"],
            "eligibility": eligibility
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
            
            for band in CANONICAL_BANDS:
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
        
    # Calculate global relative powers using 'Ratio of Means'
    # This ensures strong focal rhythms are correctly reflected in the global summary.
    psd_sums = [spectral.band_power(psd[i], freqs, TOTAL_POWER_RANGE) for i in range(len(eligible_indices))]
    avg_total_abs_30 = float(np.mean(psd_sums)) if psd_sums else 1.0
    
    global_rel_powers = {}
    for b in CANONICAL_BANDS:
        band_abs_vals = [ch["absolute_power"][b] for ch in results["channel_metrics"]]
        avg_abs = float(np.mean(band_abs_vals)) if band_abs_vals else 0.0
        global_rel_powers[b] = avg_abs / (avg_total_abs_30 + EPSILON)
    
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
