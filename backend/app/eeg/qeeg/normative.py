"""
NeuroVynx: Normative Comparison Engine
=====================================
Calculates quantitative EEG (qEEG) deviations from reference populations.

This engine computes channel-level and regional Z-scores [Z = (observed - mean) / std]
against a selected EEG reference group. 

SAFETY & COMPLIANCE:
1. NON-DIAGNOSTIC: This module never uses terms like 'abnormal' or 'pathological'.
2. TRUST-GATED: Analysis is only performed on 'trusted' signal segments.
3. REFERENCE-BASED: All interpretations are framed as 'relative to reference'.
"""

import os
import json
import numpy as np

# --------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# --------------------------------------------------------------------------

# Path to the normative reference data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NORMATIVE_DATA_PATH = os.path.join(BASE_DIR, "eeg", "qeeg", "data", "normative_reference.json")

# Z-Score Classification Config
Z_THRESHOLDS = {
    "within_range": 1.0,
    "mild": 2.0,
    "moderate": 3.0
}

# --------------------------------------------------------------------------
# CORE ENGINE FUNCTIONS
# --------------------------------------------------------------------------

def load_normative_reference():
    """Loads the normative dataset from JSON."""
    if not os.path.exists(NORMATIVE_DATA_PATH):
        return None
    
    try:
        with open(NORMATIVE_DATA_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load normative data: {e}")
        return None

def select_reference_group(reference_data, age=None, age_band=None, context="resting"):
    """
    Selects the appropriate reference group based on age or explicit band.
    Currently supports: 'adult_18_40'
    """
    if not reference_data:
        return None, "unavailable_no_reference"

    groups = reference_data.get("groups", {})
    
    # 1. Direct Band Lookup
    if age_band and age_band in groups:
        return groups[age_band], "available"

    # 2. Age-to-Band Mapping
    if age is not None:
        try:
            age_int = int(age)
            # Map age to band (MVP: one band only)
            if 18 <= age_int <= 40:
                band = "adult_18_40"
                if band in groups:
                    return groups[band], "available"
            else:
                return None, "unavailable_age_out_of_range"
        except (ValueError, TypeError):
            return None, "unavailable_invalid_age"

    return None, "unavailable_missing_age_group"

def compute_z_score(observed, mean, std):
    """Calculates z-score with safety guards."""
    if std <= 0 or observed is None or mean is None:
        return None
    return (observed - mean) / std

def classify_z_score(z):
    """
    Transforms a raw z-score into non-diagnostic descriptive wording.
    Follows strict Phase 3A safety guidelines.
    """
    if z is None:
        return "unsupported"
        
    abs_z = abs(z)
    direction = "elevated" if z > 0 else "reduced"
    
    if abs_z < Z_THRESHOLDS["within_range"]:
        return "within expected reference range"
    
    # Tiered deviation labels (Non-Diagnostic)
    if abs_z < Z_THRESHOLDS["mild"]:
        severity = "mild"
    elif abs_z < Z_THRESHOLDS["moderate"]:
        severity = "moderate"
    else:
        severity = "marked"
        
    return f"{severity} deviation {direction} relative to reference"

def compute_normative_comparison(qeeg_results, age=None, age_band=None, context="resting"):
    """
    Unified entry point for normative analysis.
    Inherits platform trust model: only allowed if trust_level == 'trusted'.
    """
    # 1. Trust Gating
    trust_level = qeeg_results.get("trust_level", "unavailable")
    if trust_level != "trusted":
        return {
            "normative_allowed": False,
            "normative_status": "unavailable_low_trust",
            "reason": "Normative comparison withheld due to signal quality / trust constraints."
        }

    # 2. Reference Selection
    ref_data = load_normative_reference()
    group_data, status = select_reference_group(ref_data, age=age, age_band=age_band, context=context)
    
    if status != "available":
        return {
            "normative_allowed": False,
            "normative_status": status,
            "reason": f"No valid normative reference found for requested group ({status})."
        }

    # 3. Compute Metrics
    regional_results = _compute_regional(qeeg_results.get("regional_metrics", []), group_data)
    channel_results = _compute_channels(qeeg_results.get("channel_metrics", []), group_data)

    # 4. Normative Topography (Phase 3B)
    # Generates a payload optimized for zero-centered spatial rendering
    topomap_results = build_normative_topomap_payload(
        channel_z_results=channel_results,
        trust_level=trust_level
    )

    # 5. Final Aggregation
    return {
        "is_available": True,
        "normative_allowed": True,
        "normative_status": "available",
        "reference_metadata": ref_data.get("metadata", {}),
        "results": {
            "regional": regional_results,
            "channels": channel_results
        },
        "topomap_layer": topomap_results,
        "summary": _generate_summary(regional_results, channel_results) # Descriptive summary
    }

def build_normative_topomap_payload(channel_z_results, trust_level):
    """
    Constructs the spatial layers for normative deviation mapping.
    
    ELIGIBILITY RULES:
    1. Signal Trust: Requires high-confidence 'trusted' status.
    2. Spatial Support: Requires at least 8 sensors with valid reference data.
    
    VISUAL RULES:
    - Symmetric Scaling: Anchored at Z=0.
    - Floor Limit: Minimum scale of 2.0 to prevent minor noise saliency.
    """
    # 1. Trust Gating
    if trust_level != "trusted":
        return {
            "is_available": False,
            "status": "unavailable_low_trust",
            "reason": "Normative deviation topography requires high-confidence signal trust."
        }

    # 2. Count Supported Channels
    supported_channels = list(channel_z_results.keys())
    if len(supported_channels) < 8:
        return {
            "is_available": False,
            "status": "unavailable_insufficient_channel_support",
            "reason": f"Insufficient normative channel support for spatial rendering ({len(supported_channels)}/8 required)."
        }

    # 3. Build Per-Band Payloads
    bands = ["delta", "theta", "alpha", "beta"]
    band_payloads = {}

    for band in bands:
        z_values = []
        ch_map = {}
        withheld_count = 0
        
        for ch, metrics in channel_z_results.items():
            if band in metrics:
                z = metrics[band]["z_score"]
                if z is not None:
                    z_values.append(z)
                    ch_map[ch] = z
                else:
                    withheld_count += 1
        
        # Calculate symmetric scale limit [ -limit, +limit ]
        # We enforce a floor (2.0) so small Z-scores don't look dramatic.
        abs_vals = [abs(z) for z in z_values] if z_values else [0]
        symmetric_limit = float(max(max(abs_vals) if abs_vals else 0, 2.0))

        band_payloads[band] = {
            "channel_z_scores": ch_map,
            "z_min": float(min(z_values)) if z_values else 0.0,
            "z_max": float(max(z_values)) if z_values else 0.0,
            "symmetric_limit": symmetric_limit,
            "supported_channel_count": len(ch_map),
            "withheld_channel_count": withheld_count
        }

    return {
        "is_available": True,
        "status": "available",
        "map_type": "normative_z_map",
        "bands": band_payloads,
        "disclaimer": "This map shows deviation from a selected EEG reference group. It does not provide a clinical diagnosis."
    }

def _compute_regional(observed_regions, group_data):
    """Calculates regional z-scores."""
    results = {}
    norms = group_data.get("regional_relative_power", {})
    
    for region_obs in observed_regions:
        region_name = region_obs["region"]
        obs_powers = region_obs["relative_power"]
        
        if region_name not in norms:
            continue
            
        region_norms = norms[region_name]
        region_z = {}
        
        for band, val in obs_powers.items():
            if band in region_norms:
                mean = region_norms[band]["mean"]
                std = region_norms[band]["std"]
                z = compute_z_score(val, mean, std)
                region_z[band] = {
                    "observed": float(val),
                    "expected_mean": float(mean),
                    "z_score": float(z) if z is not None else None,
                    "classification": classify_z_score(z)
                }
        
        results[region_name] = region_z
        
    return results

def _compute_channels(observed_channels, group_data):
    """Calculates channel-level z-scores (subset F3, F4, C3, C4, P3, P4, O1, O2)."""
    results = {}
    norms = group_data.get("channel_relative_power", {})
    
    for ch_obs in observed_channels:
        ch_name = ch_obs["channel"]
        obs_powers = ch_obs["relative_power"]
        
        if ch_name not in norms:
            continue
            
        ch_norms = norms[ch_name]
        ch_z = {}
        
        for band, val in obs_powers.items():
            if band in ch_norms:
                mean = ch_norms[band]["mean"]
                std = ch_norms[band]["std"]
                z = compute_z_score(val, mean, std)
                ch_z[band] = {
                    "observed": float(val),
                    "expected_mean": float(mean),
                    "z_score": float(z) if z is not None else None,
                    "classification": classify_z_score(z)
                }
        
        results[ch_name] = ch_z
        
    return results

def _generate_summary(regional, channels):
    """Generates non-diagnostic wording-safe summaries for the dashboard."""
    regional_deviations = []
    channel_deviations = []
    
    # 1. Regional Deviations
    for region, bands in regional.items():
        for band, metrics in bands.items():
            if metrics["classification"] != "within expected reference range":
                regional_deviations.append({
                    "region": region,
                    "band": band,
                    "z": metrics["z_score"],
                    "description": metrics["classification"]
                })

    # 2. Channel Deviations
    for ch, bands in channels.items():
        for band, metrics in bands.items():
            if metrics["classification"] != "within expected reference range":
                channel_deviations.append({
                    "channel": ch,
                    "band": band,
                    "z": metrics["z_score"],
                    "description": metrics["classification"]
                })

    # 3. Compact Ranking (Top 3 by abs Z-score)
    all_devs = regional_deviations + channel_deviations
    top_rank = sorted(all_devs, key=lambda x: abs(x["z"]) if x["z"] is not None else 0, reverse=True)[:3]

    if not all_devs:
        pattern_hint = "All supported metrics are within expected range."
    else:
        pattern_hint = f"{len(regional_deviations)} regional and {len(channel_deviations)} channel deviations detected."

    return {
        "pattern_hint": pattern_hint,
        "deviation_count": len(all_devs),
        "top_deviations": top_rank,
        "not_clinical_warning": "This panel shows deviation from a selected EEG reference group. It does not provide a clinical diagnosis."
    }
