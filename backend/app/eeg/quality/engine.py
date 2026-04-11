"""
NeuroVynx: Probabilistic Signal Quality & Artifact Detection Engine
===================================================================

This module implements the 'heuristic' core of NeuroVynx. Instead of relying on 
computationally expensive deep learning models, it utilizes robust statistics 
to detect classical EEG artifacts in real-time.

Key Concepts:
- Robust Statistics: Uses Median Absolute Deviation (MAD) instead of Standard 
  Deviation to prevent single bad channels from skewing the entire session's baseline.
- Decision Heuristics: Rule-based classification for Common Mode artifacts (clipping, 
  flatlines) and transient neurological noise (blinks).
"""

import numpy as np
from app.eeg.features import spectral

# Threshold constants for signal interpretation (values in microvolts - uV)
# --------------------------------------------------------------------------
FLATLINE_VARIANCE_TRHESH = 0.05       # Near-zero variance suggests hardware disconnect
CLIPPING_P2P_THRESH = 1000.0          # Excessive amplitude typical of amplifier saturation
HIGH_VARIANCE_THRESH = 1500.0         # General noise threshold for electrode instability
BLINK_TRANS_THRESH = 100.0            # Sharp voltage shifts characteristic of ocular blinks

# Statistical Floors & Thresholds
MIN_MAD_FLOOR = 150.0                 # Prevent MAD collapse in simulation data
BAD_CHANNEL_Z_THRESHOLD = 12.0        # Robust Z-score for bad channels
WARN_CHANNEL_Z_THRESHOLD = 6.0         # Robust Z-score for warning channels

# Global Noise Penalty Thresholds
NOISE_RATIO_WARN = 0.35               # Ratio of HighFreq (30-45Hz) to LowFreq (1-30Hz)
NOISE_RATIO_BAD = 0.60                # Severe HF contamination
NOISE_WARN_PENALTY = 15
NOISE_BAD_PENALTY = 35

def moving_average(x: np.ndarray, window: int = 7):
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
    
    Args:
        data_uv: Numpy array of EEG traces unscaled (expected in microvolts).
        channels: List of electrode names (e.g., Fp1, Oz).
        sfreq: Sampling frequency (Hz).
    """
    results = {}
    warnings = []
    
    num_channels, num_samples = data_uv.shape
    
    # Pre-compute core channel metrics: Variance (Power) and Peak-to-Peak (Amplitude)
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)
    
    # --- 1. ROBUST STATISTICAL CALIBRATION ---
    # We use Median Absolute Deviation (MAD) because it is 'breakdown resilient'.
    # If a few electrodes are completely loose (extreme variance), MAD remains 
    # stable, allowing us to accurately identify them as outliers relative to 
    # the 'working' channels.
    epsilon = 1e-12
    median_var = np.median(variances)
    mad = np.median(np.abs(variances - median_var))
    
    # Apply floor to prevent MAD collapse in clean datasets
    mad = max(mad, MIN_MAD_FLOOR)
    
    for i, ch_name in enumerate(channels):
        var = variances[i]
        ptp = p2p[i]
        
        status = "good"
        ch_warnings = []
        
        # --- HEURISTIC RULE 1: FLATLINE ---
        # Detects hardware failure or zero-signal input.
        if var < FLATLINE_VARIANCE_TRHESH:
            status = "bad"
            ch_warnings.append("Flatline / Near-Zero Variance")
            
        # --- HEURISTIC RULE 2: CLIPPING/SATURATION ---
        # Detects when the signal exceeds the amplifier's dynamic range.
        elif ptp > CLIPPING_P2P_THRESH:
            status = "bad"
            ch_warnings.append("Clipping / Saturation Detected")
            
        # --- HEURISTIC RULE 3: ROBUST OUTLIER DETECTION ---
        # Instead of standard Z-scores, we use a Robust Z-Score.
        # Channels deviating > 6*MAD are flagged as likely high-impedance or loose leads.
        z_robust = abs(var - median_var) / mad
        
        if z_robust > BAD_CHANNEL_Z_THRESHOLD:
            status = "bad"
            ch_warnings.append("Possible Electrode Instability")
        elif z_robust > WARN_CHANNEL_Z_THRESHOLD:
            status = "warning"
            ch_warnings.append("High Variance Detected")
        
        # --- HEURISTIC RULE 4: BLINK DETECTION (Frontal Electrodes) ---
        # Blinks are high-amplitude transients typically isolated to frontal leads (Fp1/Fp2).
        # We check for a sudden 'step' in voltage using the first derivative (np.diff).
        name_upper = ch_name.upper()
        if "FP1" in name_upper or "FP2" in name_upper:
            # NOISE ROBUSTNESS: Smooth signal before transient check
            smoothed_ch = moving_average(data_uv[i], window=7)
            diffs = np.abs(np.diff(smoothed_ch))
            
            # Threshold combination of transient shift (diff) and total amplitude (ptp)
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
        
        if ch_warnings:
            warnings.append(f"{ch_name}: {', '.join(ch_warnings)}")
            
    # --- 5. ABSOLUTE CONTAMINATION PENALTY (GLOBAL NOISE) ---
    # Detects broadband technical noise even if uniform across channels.
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    hf_power = spectral.band_power(psd, freqs, (30.0, 45.0))
    lf_power = spectral.band_power(psd, freqs, (1.0, 30.0))
    
    # Calculate Noise Ratio per channel
    noise_ratios = hf_power / (lf_power + 1e-12)
    global_noise_ratio = np.median(noise_ratios)
    
    global_noise_penalty = 0
    if global_noise_ratio > NOISE_RATIO_BAD:
        global_noise_penalty = NOISE_BAD_PENALTY
        warnings.append(f"Global: Severe High-Frequency Contamination (Ratio: {global_noise_ratio:.2f})")
    elif global_noise_ratio > NOISE_RATIO_WARN:
        global_noise_penalty = NOISE_WARN_PENALTY
        warnings.append(f"Global: High broadband noise detected (Ratio: {global_noise_ratio:.2f})")
    
    # --- 6. FINAL SCORING LOGIC ---
    bad_count = sum(1 for v in results.values() if v['status'] == 'bad')
    warn_count = sum(1 for v in results.values() if v['status'] == 'warning')
    
    # Total Score = 100 - (Local Abnormality) - (Global Contamination)
    score = 100 - (bad_count * 20) - (warn_count * 5) - global_noise_penalty
    score = max(0, score)
    
    return {
        "overall_quality_score": score,
        "per_channel_status": results,
        "warnings": warnings,
        "metrics_summary": {
            "bad_channels": bad_count,
            "warning_channels": warn_count,
            "global_noise_ratio": float(global_noise_ratio),
            "median_variance": float(median_var),
            "mad": float(mad)
        }
    }
