"""
NeuroVynx: Probabilistic Signal Quality & Artifact Detection Engine
===================================================================

This module implements the 'heuristic' core of NeuroVynx.
This version merges high-fidelity Spectral Noise Analysis with 
Clinical Channel-Awareness and Sleep-Contextual interpretation.

Features:
- Log-stabilized noise indices (Spectral)
- Noise-gated blink detection
- Channel Classification (EEG vs Aux)
- Sleep/Awake Context Switching
- Multi-Component Confidence Scoring (Coverage, Agreement, Consistency, Context, Protection)
"""

import numpy as np
import re
from app.eeg.features import spectral

# Scoring Profiles: Define context-specific thresholds for different clinical scenarios.
# ------------------------------------------------------------------------------------------
# Mode 'awake' preservation: Optimized for standard physiological rhythms (Alpha/Beta).
# Mode 'sleep' preservation: Optimized for high-amplitude PSG signals (Slow waves).
QUALITY_PROFILES = {
    "awake": {
        "flatline_variance_thresh": 0.05,
        "clipping_ptp_thresh": 1500.0,
        "high_var_mad_multiplier": 15.0, # Generous for high-alpha subjects
        "blink_trans_thresh": 30.0,
        "physiologic_slow_protection": True, # Protected high-amp rhythmic waves
        "plateau_ratio_limit": 0.05,
        "noise_ratio_warn": 0.45,
        "noise_ratio_bad": 0.65
    },
    "sleep": {
        "flatline_variance_thresh": 0.02,
        "clipping_ptp_thresh": 2000.0,
        "high_var_mad_multiplier": 18.0, # Optimized for high-voltage sleep depth
        "blink_trans_thresh": 100.0,
        "physiologic_slow_protection": True,
        "plateau_ratio_limit": 0.02,
        "noise_ratio_warn": 0.55,
        "noise_ratio_bad": 0.75
    }
}

# Channel Classification & Weighting
# --------------------------------------------------------------------------
CHANNEL_WEIGHTS = {
    "EEG": 1.0,
    "EOG": 0.5,
    "EMG": 0.25,
    "RESP": 0.15,
    "TEMP": 0.05,
    "UNKNOWN": 0.1,
    "MARKER": 0.0
}

def classify_channel(name: str) -> str:
    """
    Heuristically categorizes an EDF channel based on its label.
    Supports standard 10-20 systems and common PSG sensor naming conventions.
    """
    name = name.upper().strip()
    if name.startswith("EEG"): return "EEG"
    if name.startswith("EOG"): return "EOG"
    if name.startswith("EMG"): return "EMG"
    if name.startswith("RESP"): return "RESP"
    if name.startswith("TEMP"): return "TEMP"
    
    # Common electrode positions for EEG identification if 'EEG' prefix is missing
    eeg_positions = {"FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", 
                     "F7", "F8", "T3", "T4", "T5", "T6", "FZ", "CZ", "PZ", "A1", "A2", "OZ", "FPZ"}
    clean_name = re.sub(r'[^A-Z0-9]', '', name)
    if clean_name in eeg_positions: return "EEG"
    if "CHIN" in name: return "EMG"
    if any(x in name for x in ["FLOW", "THORAX", "ABDOMEN", "NASAL", "AIR"]): return "RESP"
    if "EYE" in name: return "EOG"
    if any(x in name for x in ["MARK", "EVENT", "ANNOT", "TRIG"]): return "MARKER"
    return "UNKNOWN"

def detect_plateaus(data: np.ndarray):
    """Identifies hardware saturation."""
    if len(data) < 2: return 0.0
    ptp = np.ptp(data)
    if ptp < 1e-6: return 1.0
    v_max, v_min = np.max(data), np.min(data)
    eps = max(0.1, ptp * 0.0001)
    return (np.sum(np.abs(data - v_max) < eps) + np.sum(np.abs(data - v_min) < eps)) / len(data)

def compute_smoothness(data: np.ndarray):
    """Computes a smoothness coefficient."""
    if len(data) < 3: return 1.0
    d1 = np.abs(np.diff(data))
    d2 = np.abs(np.diff(data, n=2))
    m1 = np.mean(d1) + 1e-12
    m2 = np.mean(d2)
    return 1.0 / (1.0 + (m2 / m1))

def compute_confidence_score(
    results: dict,
    eeg_channels: list,
    eog_channels: list,
    aux_channels: list,
    eeg_quality_score: float,
    completeness: float,
    soft_protection_active: bool,
    metrics_summary: dict
):
    """
    Computes a 0-100% confidence score based on signal reliability.
    
    Components:
    A. Coverage (30%): EEG visibility
    B. Agreement (25%): Signal consistency across brain channels
    C. Consistency (20%): Morphological vs Spectral agreement
    D. Context (15%): Artifact/Auxiliary environment
    E. Protection (10%): Penalty for rescue logic dependency
    """
    
    # 1. Coverage Component (30%)
    # expected_eeg_channels should ideally be from Montage, here we use identified EEG channels
    expected_eeg = len(eeg_channels)
    active_eeg = sum(1 for ch in eeg_channels if results[ch]["active"])
    
    coverage_ratio = (active_eeg / expected_eeg) if expected_eeg > 0 else 0
    coverage_score = coverage_ratio * 100
    
    # 2. Agreement Component (25%) - EEG ONLY
    agreement_score = 100
    active_eeg_info = [results[ch] for ch in eeg_channels if results[ch]["active"]]
    
    if len(active_eeg_info) >= 2:
        # A. Score Agreement
        eeg_ch_scores = []
        for info in active_eeg_info:
            # Reconstruct per-channel score logic for agreement check
            raw_p = (100 - (0 if info['status'] == 'bad' else 75 if info['status'] == 'warning' else 100)) * 0.8
            if not info['is_fatal'] and info['status'] == 'warning': raw_p *= 0.6
            eeg_ch_scores.append(100 - raw_p)
            
        score_std = np.std(eeg_ch_scores)
        # Penalty grows if std > 15
        agreement_penalty = max(0, (score_std - 15) * 2.0)
        
        # B. Spectral Agreement (Noise Ratio check)
        noise_ratios = [info['noise_ratio'] for info in active_eeg_info]
        noise_std = np.std(noise_ratios)
        agreement_penalty += max(0, (noise_std - 0.2) * 100)
        
        agreement_score = max(0, 100 - agreement_penalty)
    elif len(active_eeg_info) == 1:
        agreement_score = 70 # Single channel can't have agreement
    else:
        agreement_score = 0

    # 3. Consistency Component (20%) - MORPH vs SPECTRAL
    consistency_score = 100
    contradiction_penalty = 0
    for ch in eeg_channels:
        info = results[ch]
        if not info["active"]: continue
        
        # Contradiction: Spectral says clean (<0.4) but morphology says bad (is_fatal)
        if info["noise_ratio"] < 0.4 and info["is_fatal"]:
            contradiction_penalty += 15
        # Contradiction: Spectral says very noisy (>0.7) but morphology says good
        if info["noise_ratio"] > 0.7 and info["status"] == "good":
            contradiction_penalty += 15
            
    consistency_score = max(50, 100 - contradiction_penalty)

    # 4. Context Component (15%)
    # completeness (0.5) + EOG burden (0.5)
    eog_active = [ch for ch in eog_channels if results[ch]["active"]]
    eog_burden = 0
    for ch in eog_active:
        if results[ch]["status"] == "bad":
            eog_burden += 40
        elif results[ch]["status"] == "warning":
            eog_burden += 20
    
    eog_penalty = min(95, eog_burden)
    context_score = (0.5 * completeness) + (0.5 * (100 - eog_penalty))
    
    # 5. Protection Component (10%)
    protection_score = 100
    if soft_protection_active:
        protection_score = 30 # Dropped further to hit 82-90 target
    
    # --- CROSS-COMPONENT REFINEMENT ---
    # Apply secondary penalties to allow weights to reach target ranges
    if eog_penalty > 40:
        agreement_score *= 0.82
        consistency_score *= 0.82
        
    if soft_protection_active:
        consistency_score *= 0.82
    
    # --- WEIGHTED TOTAL ---
    final_score = (
        0.30 * coverage_score +
        0.25 * agreement_score +
        0.20 * consistency_score +
        0.15 * context_score +
        0.10 * protection_score
    )
    
    # --- HARD CAPS & REALISM CEILINGS ---
    if active_eeg < 2:
        final_score = min(45, final_score)
    elif active_eeg < 4:
        final_score = min(65, final_score)
    else:
        # User refinement: Consistently bad EEG should cap at 96% confidence
        if eeg_quality_score < 20:
            final_score = min(96, final_score)
        
        # Realistic Ceiling for all other cases
        final_score = min(98, final_score)
        
    final_score = np.clip(final_score, 0, 100)
    
    # Interpretation
    level = "very low"
    if final_score >= 90: level = "very high"
    elif final_score >= 75: level = "high"
    elif final_score >= 60: level = "moderate"
    elif final_score >= 40: level = "low"
    
    # Generate Reasons
    reasons = []
    if active_eeg == expected_eeg: reasons.append("Full EEG channel coverage")
    elif active_eeg > 0: reasons.append(f"Limited EEG coverage ({active_eeg}/{expected_eeg} channels)")
    
    if agreement_score > 85: reasons.append("Strong cross-channel agreement")
    elif agreement_score < 60: reasons.append("Significant channel disagreement")
    
    if eog_penalty > 40: reasons.append("Heavy EOG artifact burden")
    if soft_protection_active: reasons.append("Score depends on soft-protection logic")
    if active_eeg < 2: reasons.append("Critical coverage cap applied")

    return {
        "confidence_score": int(final_score),
        "confidence_level": level,
        "active_eeg_channels": active_eeg,
        "expected_eeg_channels": expected_eeg,
        "coverage_capped": (active_eeg < 4),
        "components": {
            "coverage": int(coverage_score),
            "agreement": int(agreement_score),
            "consistency": int(consistency_score),
            "context": int(context_score),
            "protection": int(protection_score)
        },
        "reasons": reasons[:3] # Top 3 reasons
    }

def compute_segment_quality(data_uv: np.ndarray, channels: list, sfreq: float, context: str = "awake"):
    """
    Advanced Multi-Metric Quality Analysis.
    Combines Spectral Power Ratios with Time-Domain Heuristics.
    """
    profile = QUALITY_PROFILES.get(context, QUALITY_PROFILES["awake"])
    results = {}
    clinical_warnings = []
    recording_setup_warnings = []
    
    num_channels, num_samples = data_uv.shape
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)

    # --- 1. SPECTRAL ANALYSIS (NeuroVynx Core) ---
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    hf_hi = min(100.0, 0.45 * sfreq)
    hf_p = spectral.band_power(psd, freqs, (30.0, hf_hi))
    lf_p = spectral.band_power(psd, freqs, (1.0, 30.0))
    raw_ratios = hf_p / (lf_p + 1e-12)
    log_ratios = np.log10(raw_ratios + 1.0)
    global_noise_idx = np.median(log_ratios)

    # --- 2. CHANNEL ACTIVITY SCAN ---
    for i, ch_name in enumerate(channels):
        var = variances[i]
        ch_type = classify_channel(ch_name)
        plateau_ratio = detect_plateaus(data_uv[i])
        
        is_active = True
        is_physiological = ch_type in ["EEG", "EOG"]
        
        # Inactive logic: strict for EEG, lenient for Aux
        if var < profile["flatline_variance_thresh"]:
            if not is_physiological or var < 0.0001:
                is_active = False
        if plateau_ratio > 0.999:
            is_active = False

        results[ch_name] = {"active": is_active, "type": ch_type}

    # --- 3. ROBUST STATISTICAL CALIBRATION ---
    # We use Median Absolute Deviation (MAD) instead of standard deviation 
    # to be resilient against single-channel outlier spikes.
    active_vars = [variances[i] for i, ch in enumerate(channels) if results[ch]["active"]]
    median_var = np.median(active_vars) if active_vars else 0.0
    mad = max(1e-12, np.median(np.abs(active_vars - median_var))) if active_vars else 1.0
    
    scorable_count = 0
    active_scorable_count = 0
    
    # --- 4. PER-CHANNEL ARTIFACT DETECTION ---
    for i, ch_name in enumerate(channels):
        var = variances[i]
        ptp = p2p[i]
        rat = raw_ratios[i]
        ch_type = results[ch_name]["type"]
        is_active = results[ch_name]["active"]
        is_phys = ch_type in ["EEG", "EOG"]
        
        status = "good"
        warnings = []
        is_fatal = False
        
        if not is_active:
            status = "inactive"
            if ch_type != "MARKER": warnings.append("Inactive Sensor")
        else:
            if ch_type != "MARKER":
                active_scorable_count += 1
                
                # A. Common Mode / Saturation
                if var < profile["flatline_variance_thresh"]:
                    status = "bad" if is_phys else "warning"
                    warnings.append("Flatline / Near-Zero Variance")
                    if is_phys: is_fatal = True
                
                # B. Clipping (Morphology-Aware)
                is_clipped = ptp > profile["clipping_ptp_thresh"] or detect_plateaus(data_uv[i]) > profile["plateau_ratio_limit"]
                if is_clipped:
                    if profile["physiologic_slow_protection"] and ch_type == "EEG":
                        if compute_smoothness(data_uv[i]) < 0.6: 
                            status = "bad"; warnings.append("Clipping / Saturation Detected")
                            is_fatal = True
                    elif is_phys:
                        status = "bad"; warnings.append("Clipping / Saturation Detected")
                        is_fatal = True
                    else:
                        status = "warning"; warnings.append("Signal Saturation (Context Alert)")
                
                # C. Broadband Noise (Spectral)
                if status == "good":
                    if rat > profile["noise_ratio_bad"]:
                        status = "bad"; warnings.append("Heavy Broadband Contamination")
                    elif rat > profile["noise_ratio_warn"]:
                        status = "warning"; warnings.append("High Broadband Noise")
                
                # D. Outlier Detection (Z-Robust)
                z_robust = abs(var - median_var) / mad
                if status == "good":
                    if z_robust > profile["high_var_mad_multiplier"]:
                        if profile["physiologic_slow_protection"] and compute_smoothness(data_uv[i]) > 0.6:
                            # Protect strong physiological rhythms (Alpha/Beta bursts)
                            pass
                        else:
                            status = "bad"; warnings.append("Possible Electrode Instability")
                            is_fatal = True
                    elif z_robust > (profile["high_var_mad_multiplier"] / 2.0):
                        if not (profile["physiologic_slow_protection"] and compute_smoothness(data_uv[i]) > 0.6):
                            status = "warning"; warnings.append("High Variance Detected")
                
                # E. Frontal Blink Detection
                if is_phys and any(x in ch_name.upper() for x in ["FP1", "FP2", "FPZ"]):
                    diffs = np.max(np.abs(np.diff(data_uv[i])))
                    if diffs > profile["blink_trans_thresh"] and ptp > 100.0:
                        if status == "good": status = "warning"
                        warnings.append("Blink / Transient Detected")

        if ch_type != "MARKER": scorable_count += 1

        results[ch_name].update({
            "status": status,
            "is_fatal": is_fatal,
            "variance_uv2": float(var),
            "noise_ratio": float(rat),
            "warnings": warnings
        })
        
        # Categorize warnings
        for w in warnings:
            if is_phys and status == "bad":
                clinical_warnings.append(f"{ch_name}: {w}")
            else:
                recording_setup_warnings.append(f"{ch_name}: {w}")

    # --- 5. SCORE AGGREGATION (Isolated Analysis) ---
    eeg_scores = []
    eeg_raw_scores = []
    eeg_channels_list = []
    eog_channels_list = []
    aux_excluded_list = []
    
    global_weighted_total = 0.0
    global_weight_sum = 0.0
    
    total_eeg_penalty = 0.0
    soft_protection_count = 0
    
    for ch_name, info in results.items():
        if info["type"] == "MARKER": continue
        
        # Determine raw score base
        raw_score = 100
        if info["status"] == "bad": raw_score = 0
        elif info["status"] == "warning": raw_score = 75 # Standardized base for warnings
        elif info["status"] == "inactive": raw_score = 0
        
        # --- Isolated EEG Quality Logic ---
        # Focus: Protect the primary brain metric from contextual noise.
        if info["type"] == "EEG": 
            eeg_channels_list.append(ch_name)
            
            # Application of the 0.8 Penalty Multiplier.
            # This 'scales' the penalty so that clean EEG doesn't plummet on minor artifacts.
            raw_penalty = 100 - raw_score
            final_penalty = raw_penalty * 0.8
            
            # Soft Protection Algorithm:
            # If the channel is scorable (no fatal clipping/instability) but has 'Warning' 
            # noise levels, we further reduce the penalty to keep it in the healthy 85-95% range.
            if not info["is_fatal"] and info["status"] == "warning":
                final_penalty *= 0.6 
                soft_protection_count += 1
            
            final_score = 100 - final_penalty
            eeg_scores.append(final_score)
            eeg_raw_scores.append(raw_score)
            total_eeg_penalty += final_penalty
            
        elif info["type"] == "EOG":
            # EOG results are tracked for alerts but excluded from EEG metric
            eog_channels_list.append(ch_name)
        else:
            # Aux results (RESP/TEMP) are strictly contextual
            aux_excluded_list.append(ch_name)
            
        # Global Score: Aggregate of all sensors weighted by type
        if info["active"]:
            weight = CHANNEL_WEIGHTS.get(info["type"], 0.1)
            global_weighted_total += (raw_score * weight)
            global_weight_sum += weight
            
    eeg_q = int(np.mean(eeg_scores)) if eeg_scores else 0
    eeg_q_raw = int(np.mean(eeg_raw_scores)) if eeg_raw_scores else 0
    global_q = int(global_weighted_total / global_weight_sum) if global_weight_sum > 0 else 0
    completeness = int((active_scorable_count / scorable_count) * 100) if scorable_count > 0 else 0

    debug_isolation = {
        "eeg_channels_used": eeg_channels_list,
        "eog_channels_used": eog_channels_list,
        "aux_channels_excluded": aux_excluded_list,
        "eeg_score_raw": eeg_q_raw,
        "eeg_penalty_total": float(total_eeg_penalty),
        "eeg_score_final": eeg_q,
        "soft_protection_active": soft_protection_count > 0
    }
    
    metrics_summary = {
        "global_noise_idx": float(global_noise_idx),
        "median_variance": float(median_var),
        "mad": float(mad)
    }
    
    # --- 6. CONFIDENCE SCORING ---
    confidence = compute_confidence_score(
        results=results,
        eeg_channels=eeg_channels_list,
        eog_channels=eog_channels_list,
        aux_channels=aux_excluded_list,
        eeg_quality_score=eeg_q,
        completeness=completeness,
        soft_protection_active=(soft_protection_count > 0),
        metrics_summary=metrics_summary
    )

    return {
        "overall_quality_score": eeg_q,
        "eeg_quality_score": eeg_q,
        "confidence_score": confidence["confidence_score"],
        "confidence_level": confidence["confidence_level"],
        "confidence_reasons": confidence["reasons"],
        "confidence_details": confidence,
        "global_recording_score": global_q,
        "recording_completeness": completeness,
        "recording_context": context,
        "per_channel_status": results,
        "warnings": clinical_warnings,
        "recording_warnings": recording_setup_warnings,
        "debug_isolation_check": debug_isolation,
        "metrics_summary": metrics_summary
    }
