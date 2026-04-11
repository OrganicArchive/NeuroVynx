"""
NeuroVynx: Probabilistic Signal Quality & Artifact Detection Engine
===================================================================

FINAL STABLE VERSION
- Log-stabilized noise indices
- Noise-gated blink detection (prevents false blinks in junk data)
- Synchronized visual-logical scoring thresholds
"""

import numpy as np
from app.eeg.features import spectral

# --------------------------------------------------------------------------
# CONFIG (STABLE CALIBRATION)
# --------------------------------------------------------------------------
BLINK_SMOOTH_WINDOW = 3
BLINK_WINDOW_SEC = 0.02
BLINK_TRANS_THRESH = 30.0             # Slope threshold (µV shift over 20ms)

NOISE_RATIO_WARN = 0.45               # Ratio (HighFreq/LowFreq)
NOISE_RATIO_BAD = 0.65

NOISE_WARN_PENALTY = 25
NOISE_BAD_PENALTY = 50
LINE_NOISE_PENALTY = 40

CHANNEL_VAR_WARN = 800.0              # Absolute variance thresholds (µV²)
CHANNEL_VAR_BAD = 1500.0

MIN_MAD_FLOOR = 150.0
MAX_SCORE = 100
MIN_SCORE = 0

def moving_average(x: np.ndarray, w: int):
    """Simple temporal smoothing."""
    if w <= 1: return x
    return np.convolve(x, np.ones(w)/w, mode="same")

def compute_segment_quality(data_uv: np.ndarray, channels: list, sfreq: float):
    """
    Main entry point for NeuroVynx quality analysis.
    Synchronizes logical scoring with visual channel status.
    """
    results = {}
    warnings = []
    
    num_channels, num_samples = data_uv.shape
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)
    
    # --- 1. SPECTRAL PRE-COMPUTATION ---
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    
    # Metrics for HF/LF ratio (30-100Hz / 1-30Hz)
    hf_hi = min(100.0, 0.45 * sfreq)
    hf_p = spectral.band_power(psd, freqs, (30.0, hf_hi))
    lf_p = spectral.band_power(psd, freqs, (1.0, 30.0))
    
    # Calculate Log-Stabilized Ratios per channel
    raw_ratios = hf_p / (lf_p + 1e-12)
    log_ratios = np.log10(raw_ratios + 1.0)
    
    # --- 2. GLOBAL NOISE ANALYSIS ---
    # Global noise is the median of log-stabilized channel ratios
    global_noise_idx = np.median(log_ratios)
    
    # Global Penalty Logic
    global_noise_penalty = 0
    if global_noise_idx > np.log10(NOISE_RATIO_BAD + 1.0):
        global_noise_penalty = NOISE_BAD_PENALTY
        warnings.append(f"Global: Severe Broadband Contamination (Log-Idx: {global_noise_idx:.2f})")
    elif global_noise_idx > np.log10(NOISE_RATIO_WARN + 1.0):
        global_noise_penalty = NOISE_WARN_PENALTY
        warnings.append(f"Global: High broadband noise detected (Log-Idx: {global_noise_idx:.2f})")

    # --- 3. PER-CHANNEL STATUS & BLINKS ---
    # Robust baseline for outlier detection
    median_var = np.median(variances)
    mad = np.median(np.abs(variances - median_var))
    mad = max(mad, MIN_MAD_FLOOR)

    blink_penalty = 0
    blink_detected = False
    
    for i, ch_name in enumerate(channels):
        var = variances[i]
        ptp = p2p[i]
        rat = raw_ratios[i] # Use raw ratio for absolute channel thresholds
        
        status = "good"
        ch_warnings = []
        
        # A. Hardware failure / saturation
        if var < 0.05: # Flatline
            status = "bad"
            ch_warnings.append("Flatline / Near-Zero Variance")
        elif ptp > 1000.0: # Clipping
            status = "bad"
            ch_warnings.append("Clipping / Saturation Detected")
            
        # B. Absolute Contamination (Visual Sync)
        if status == "good":
            if rat > NOISE_RATIO_BAD or var > CHANNEL_VAR_BAD:
                status = "bad"
                ch_warnings.append("Heavy Signal Contamination")
            elif rat > NOISE_RATIO_WARN or var > CHANNEL_VAR_WARN:
                status = "warning"
                ch_warnings.append("High Broadband Noise")

        # C. Robust Outlier Check
        if status == "good":
            z_robust = abs(var - median_var) / mad
            if z_robust > 12.0:
                status = "bad"
                ch_warnings.append("Possible Electrode Instability")
            elif z_robust > 6.0:
                status = "warning"
                ch_warnings.append("High Variance Detected")
        else:
            z_robust = abs(var - median_var) / mad
        
        # D. Noise-Gated Blink Detection
        # Blinks are only checked if the whole segment isn't already junk
        if status != "bad" and global_noise_idx < np.log10(NOISE_RATIO_BAD + 1.0):
            name_upper = ch_name.upper()
            if "FP1" in name_upper or "FP2" in name_upper:
                x_smooth = moving_average(data_uv[i], BLINK_SMOOTH_WINDOW)
                win = max(2, int(BLINK_WINDOW_SEC * sfreq))
                delta = np.abs(x_smooth[win:] - x_smooth[:-win])
                peak_shift = np.max(delta) if len(delta) else 0.0
                
                if peak_shift > BLINK_TRANS_THRESH and ptp > 100.0:
                    if status == "good": status = "warning"
                    ch_warnings.append("Blink / Transient Detected")
                    blink_penalty += 5
                    blink_detected = True
                
        results[ch_name] = {
            "status": status,
            "variance_uv2": float(var),
            "peak_to_peak_uv": float(ptp),
            "noise_ratio": float(rat),
            "z_score_robust": float(z_robust),
            "warnings": ch_warnings
        }

    # --- 4. LINE NOISE DETECTION ---
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

    # --- 5. FINAL SCORING ---
    # Score = 100 - Penalties
    score = 100 - global_noise_penalty - line_penalty - blink_penalty
    
    # Penalize based on channel health states
    bad_count = sum(1 for v in results.values() if v['status'] == 'bad')
    warn_count = sum(1 for v in results.values() if v['status'] == 'warning')
    score -= (bad_count * 10) + (warn_count * 5)
    
    score = max(0, min(100, score))
    
    return {
        "overall_quality_score": score,
        "per_channel_status": results,
        "warnings": warnings + [w for v in results.values() for w in v['warnings']],
        "metrics_summary": {
            "bad_channels": bad_count,
            "warning_channels": warn_count,
            "global_noise_idx": float(global_noise_idx),
            "line_noise_detected": line_detected,
            "blink_detected": blink_detected,
            "median_variance": float(median_var),
            "mad": float(mad)
        }
    }
