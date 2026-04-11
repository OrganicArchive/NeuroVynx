"""
NeuroSight: Probabilistic Signal Quality & Artifact Detection Engine
===================================================================

This module implements the 'heuristic' core of NeuroSight. It utilizes robust 
statistics and frequency-domain analysis to detect EEG artifacts in real-time.
"""

import numpy as np
from app.eeg.features import spectral

# --------------------------------------------------------------------------
# CONFIG (CALIBRATED FOR REALISTIC EEG)
# --------------------------------------------------------------------------
FLATLINE_VARIANCE_THRESH = 0.05
CLIPPING_P2P_THRESH = 1000.0
HIGH_VARIANCE_THRESH = 1500.0         # Absolute "Bad" variance threshold
WARN_VARIANCE_THRESH = 800.0          # Absolute "Warning" variance threshold
BLINK_TRANS_THRESH = 100.0            # Total shift over 20ms window

# Statistical Floors & Thresholds
MIN_MAD_FLOOR = 150.0
BAD_CHANNEL_Z_THRESHOLD = 12.0
WARN_CHANNEL_Z_THRESHOLD = 6.0

# Global Noise Penalty Thresholds (Calibrated to allow normal 1/f slope)
NOISE_RATIO_WARN = 0.45               # Ratio of HighFreq to LowFreq
NOISE_RATIO_BAD = 0.65
NOISE_WARN_PENALTY = 25
NOISE_BAD_PENALTY = 50

# Specialized Line Noise Detection (50Hz / 60Hz)
LINE_NOISE_PENALTY = 40

def moving_average(x: np.ndarray, window: int = 3):
    """Simple temporal smoothing."""
    if window <= 1: return x
    kernel = np.ones(window) / window
    return np.convolve(x, kernel, mode="same")

def compute_segment_quality(data_uv: np.ndarray, channels: list, sfreq: float):
    """
    Analyzes a multi-channel EEG segment for technical signal quality.
    Synchronizes logical scoring with visual trace coloring.
    """
    results = {}
    warnings = []
    
    num_channels, num_samples = data_uv.shape
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)
    
    # --- 1. SPECTRAL PRE-COMPUTATION ---
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    # Global Noise Ratio (30-100Hz / 1-30Hz)
    hf_hi = min(100.0, 0.45 * sfreq)
    hf_p = spectral.band_power(psd, freqs, (30.0, hf_hi))
    lf_p = spectral.band_power(psd, freqs, (1.0, 30.0))
    channel_noise_ratios = hf_p / (lf_p + 1e-12)
    
    # --- 2. ROBUST STATISTICAL CALIBRATION ---
    median_var = np.median(variances)
    mad = np.median(np.abs(variances - median_var))
    mad = max(mad, MIN_MAD_FLOOR)
    
    for i, ch_name in enumerate(channels):
        var = variances[i]
        ptp = p2p[i]
        rat = channel_noise_ratios[i]
        
        status = "good"
        ch_warnings = []
        
        # --- RULE A: FLATLINE/CLIPPING ---
        if var < FLATLINE_VARIANCE_THRESH:
            status = "bad"
            ch_warnings.append("Flatline / Near-Zero Variance")
        elif ptp > CLIPPING_P2P_THRESH:
            status = "bad"
            ch_warnings.append("Clipping / Saturation Detected")
            
        # --- RULE B: ABSOLUTE NOISE STATUS (Visual Sync) ---
        if status == "good":
            if rat > NOISE_RATIO_BAD or var > HIGH_VARIANCE_THRESH:
                status = "bad"
                ch_warnings.append("Heavy Signal Contamination")
            elif rat > NOISE_RATIO_WARN or var > WARN_VARIANCE_THRESH:
                status = "warning"
                ch_warnings.append("High Broadband Noise")

        # --- RULE C: ROBUST OUTLIER DETECTION ---
        if status == "good":
            z_robust = abs(var - median_var) / mad
            if z_robust > BAD_CHANNEL_Z_THRESHOLD:
                status = "bad"
                ch_warnings.append("Possible Electrode Instability")
            elif z_robust > WARN_CHANNEL_Z_THRESHOLD:
                status = "warning"
                ch_warnings.append("High Variance Detected")
        else:
            z_robust = abs(var - median_var) / mad # Still calc for metrics
        
        # --- RULE D: WAVE-AWARE BLINK DETECTION ---
        name_upper = ch_name.upper()
        if "FP1" in name_upper or "FP2" in name_upper:
            # Check slope over a 20ms window (~5 samples)
            window_size = int(0.02 * sfreq) # 20ms
            if window_size < 1: window_size = 1
            # Rolling diff
            rolled_diff = np.abs(data_uv[i, window_size:] - data_uv[i, :-window_size])
            if np.max(rolled_diff) > BLINK_TRANS_THRESH and ptp > 100.0:
                if status == "good": status = "warning"
                ch_warnings.append("Blink / Transient Detected")
                
        results[ch_name] = {
            "status": status,
            "variance_uv2": float(var),
            "peak_to_peak_uv": float(ptp),
            "noise_ratio": float(rat),
            "z_score_robust": float(z_robust),
            "warnings": ch_warnings
        }
        
    # --- 3. GLOBAL PENALTY CALCULATION ---
    global_noise_ratio = np.median(channel_noise_ratios)
    global_noise_penalty = 0
    if global_noise_ratio > NOISE_RATIO_BAD:
        global_noise_penalty = NOISE_BAD_PENALTY
        warnings.append(f"Global: Severe Broadband Contamination (Ratio: {global_noise_ratio:.2f})")
    elif global_noise_ratio > NOISE_RATIO_WARN:
        global_noise_penalty = NOISE_WARN_PENALTY
        warnings.append(f"Global: High broadband noise detected (Ratio: {global_noise_ratio:.2f})")

    # Line Noise Detection
    line_penalty = 0
    line_detected = False
    for lf in [50.0, 60.0]:
        if lf > 0.45 * sfreq: continue
        band = spectral.band_power(psd, freqs, (lf - 1.0, lf + 1.0))
        neighbor = spectral.band_power(psd, freqs, (lf - 5.0, lf + 5.0)) - band
        if np.max(band / (neighbor + 1e-12)) > 3.0:
            line_detected = True
            line_penalty = LINE_NOISE_PENALTY
            warnings.append(f"Global: Strong AC Interference detected ({lf}Hz)")
            break

    # --- 4. FINAL SCORING ---
    bad_count = sum(1 for v in results.values() if v['status'] == 'bad')
    warn_count = sum(1 for v in results.values() if v['status'] == 'warning')
    
    score = 100 - (bad_count * 10) - (warn_count * 5) - global_noise_penalty - line_penalty
    score = max(0, score)
    
    return {
        "overall_quality_score": score,
        "per_channel_status": results,
        "warnings": warnings + [w for v in results.values() for w in v['warnings']],
        "metrics_summary": {
            "bad_channels": bad_count,
            "warning_channels": warn_count,
            "global_noise_ratio": float(global_noise_ratio),
            "line_noise_detected": line_detected,
            "median_variance": float(median_var),
            "mad": float(mad)
        }
    }
