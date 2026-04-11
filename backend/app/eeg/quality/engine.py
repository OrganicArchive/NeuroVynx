"""
NeuroSight: Probabilistic Signal Quality & Artifact Detection Engine
===================================================================

This module implements the 'heuristic' core of NeuroSight. Instead of relying on 
computationally expensive deep learning models, it utilizes robust statistics 
to detect classical EEG artifacts in real-time.
"""

import numpy as np
from app.eeg.features import spectral

# --------------------------------------------------------------------------
# CONFIG (TUNE AS NEEDED)
# --------------------------------------------------------------------------
# Threshold constants for signal interpretation (values in microvolts - uV)
FLATLINE_VARIANCE_THRESH = 0.05       # Near-zero variance suggests hardware disconnect
CLIPPING_P2P_THRESH = 1000.0          # Excessive amplitude typical of amplifier saturation
HIGH_VARIANCE_THRESH = 1500.0         # General noise threshold for electrode instability
BLINK_TRANS_THRESH = 80.0             # Sharp voltage shifts characteristic of ocular blinks

# Statistical Floors & Thresholds
MIN_MAD_FLOOR = 150.0                 # Prevent MAD collapse in simulation data
BAD_CHANNEL_Z_THRESHOLD = 12.0        # Robust Z-score for bad channels
WARN_CHANNEL_Z_THRESHOLD = 6.0         # Robust Z-score for warning channels

# Global Noise Penalty Thresholds
NOISE_RATIO_WARN = 0.30
NOISE_RATIO_BAD = 0.45
NOISE_WARN_PENALTY = 25
NOISE_BAD_PENALTY = 50

# Specialized Line Noise Detection (50Hz / 60Hz)
LINE_NOISE_PENALTY = 40

def moving_average(x: np.ndarray, window: int = 3):
    """Simple temporal smoothing for noise-robust artifact detection."""
    if window <= 1:
        return x
    kernel = np.ones(window) / window
    return np.convolve(x, kernel, mode="same")

def compute_segment_quality(data_uv: np.ndarray, channels: list, sfreq: float):
    """
    Analyzes a multi-channel EEG segment for technical signal quality.
    
    The engine computes a 'Confidence Score' (0-100) per segment, which scales
    the reliability of subsequent neural feature extraction.
    """
    results = {}
    warnings = []
    
    num_channels, num_samples = data_uv.shape
    
    # Pre-compute core channel metrics
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)
    
    # --- 1. ROBUST STATISTICAL CALIBRATION ---
    median_var = np.median(variances)
    mad = np.median(np.abs(variances - median_var))
    mad = max(mad, MIN_MAD_FLOOR) # Apply floor to prevent MAD collapse
    
    for i, ch_name in enumerate(channels):
        var = variances[i]
        ptp = p2p[i]
        
        status = "good"
        ch_warnings = []
        
        # --- HEURISTIC RULE 1: FLATLINE ---
        if var < FLATLINE_VARIANCE_THRESH:
            status = "bad"
            ch_warnings.append("Flatline / Near-Zero Variance")
            
        # --- HEURISTIC RULE 2: CLIPPING/SATURATION ---
        elif ptp > CLIPPING_P2P_THRESH:
            status = "bad"
            ch_warnings.append("Clipping / Saturation Detected")
            
        # --- HEURISTIC RULE 3: ROBUST OUTLIER DETECTION ---
        z_robust = abs(var - median_var) / mad
        
        if z_robust > BAD_CHANNEL_Z_THRESHOLD:
            status = "bad"
            ch_warnings.append("Possible Electrode Instability")
        elif z_robust > WARN_CHANNEL_Z_THRESHOLD:
            status = "warning"
            ch_warnings.append("High Variance Detected")
        
        # --- HEURISTIC RULE 4: BLINK DETECTION (Frontal Electrodes) ---
        name_upper = ch_name.upper()
        if "FP1" in name_upper or "FP2" in name_upper:
            # NOISE ROBUSTNESS: Smooth signal before transient check
            smoothed_ch = moving_average(data_uv[i], window=3)
            diffs = np.abs(np.diff(smoothed_ch))
            
            if np.max(diffs) > (BLINK_TRANS_THRESH / 2.0) and ptp > BLINK_TRANS_THRESH:
                if status == "good": 
                    status = "warning"
                ch_warnings.append("Blink / Transient Detected")
                
        results[ch_name] = {
            "status": status,
            "variance_uv2": float(var),
            "peak_to_peak_uv": float(ptp),
            "z_score_robust": float(z_robust),
            "warnings": ch_warnings
        }
        
    # --- 2. GLOBAL NOISE DETECTION (Full Spectrum) ---
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    # Ratio: HighFreq (30-100Hz) to LowFreq (1-30Hz)
    hf_hi = min(100.0, 0.45 * sfreq)
    hf_power = spectral.band_power(psd, freqs, (30.0, hf_hi))
    lf_power = spectral.band_power(psd, freqs, (1.0, 30.0))
    
    noise_ratios = hf_power / (lf_power + 1e-12)
    global_noise_ratio = np.median(noise_ratios)
    
    global_noise_penalty = 0
    if global_noise_ratio > NOISE_RATIO_BAD:
        global_noise_penalty = NOISE_BAD_PENALTY
        warnings.append(f"Global: Severe Broadband Contamination (Ratio: {global_noise_ratio:.2f})")
    elif global_noise_ratio > NOISE_RATIO_WARN:
        global_noise_penalty = NOISE_WARN_PENALTY
        warnings.append(f"Global: High broadband noise detected (Ratio: {global_noise_ratio:.2f})")

    # --- 3. SPECIALIZED LINE NOISE DETECTION (50Hz / 60Hz) ---
    line_penalty = 0
    line_freqs = [50.0, 60.0]
    line_detected = False
    
    for lf in line_freqs:
        if lf > 0.45 * sfreq: continue
        # Narrow band vs. neighbors
        band = spectral.band_power(psd, freqs, (lf - 1.0, lf + 1.0))
        neighbor = spectral.band_power(psd, freqs, (lf - 5.0, lf + 5.0)) - band
        
        # Calculate peak-to-neighbor ratio across all channels
        peak_ratios = band / (neighbor + 1e-12)
        if np.max(peak_ratios) > 3.0: # Strong narrow spike found in at least one channel
            line_detected = True
            line_penalty = LINE_NOISE_PENALTY
            warnings.append(f"Global: Strong AC Interference detected ({lf}Hz)")
            break

    # --- 4. FINAL SCORING LOGIC ---
    bad_count = sum(1 for v in results.values() if v['status'] == 'bad')
    warn_count = sum(1 for v in results.values() if v['status'] == 'warning')
    
    # Total Score = 100 - (Local Abnormality) - (Global Contamination)
    score = 100 - (bad_count * 20) - (warn_count * 5) - global_noise_penalty - line_penalty
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
