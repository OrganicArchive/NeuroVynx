import numpy as np
from app.eeg.features import spectral

# Standard clinical EEG bands
BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0)
}

def extract_features(data_uv: np.ndarray, sfreq: float, channels: list):
    """
    Extracts features for an N-channel EEG segment.
    data_uv: numpy array of shape (n_channels, n_samples)
    """
    n_channels, n_samples = data_uv.shape
    
    # 1. Compute PSD efficiently vectorized across all channels
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    
    # Total power between 0.5 and 45.0 for relative power calculations
    total_power = spectral.band_power(psd, freqs, (0.5, 45.0))
    
    # Pre-calculate band powers for all channels simultaneously
    band_powers = {}
    rel_band_powers = {}
    for band_name, freq_range in BANDS.items():
        bp = spectral.band_power(psd, freqs, freq_range)
        band_powers[band_name] = bp
        rel_band_powers[band_name] = spectral.relative_power(bp, total_power)
        
    # Time-domain features
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)
    rms = np.sqrt(np.mean(np.square(data_uv), axis=1))
    max_slope = np.max(np.abs(np.diff(data_uv, axis=1)), axis=1)
    
    # Identification of Frontal/Posterior/Left/Right for spatial ratios
    frontal_indices = []
    posterior_indices = []
    left_indices = []
    right_indices = []
    
    for i, ch in enumerate(channels):
        name = ch.upper()
        # Frontal: Fp, F (simplified heuristic)
        if "FP" in name or (name.startswith("F") and not name.startswith("FC")):
            frontal_indices.append(i)
        # Posterior: P, O, T5, T6
        if "P" in name or "O" in name or "T5" in name or "T6" in name:
            posterior_indices.append(i)
        
        # Left (Odd labels: 1, 3, 5, 7) or Right (Even labels: 2, 4, 6, 8)
        import re
        num_match = re.search(r'\d+', name)
        if num_match:
            num = int(num_match.group())
            if num % 2 != 0:
                left_indices.append(i)
            else:
                right_indices.append(i)

    # Package into per-channel dict
    per_channel = {}
    
    for i, ch_name in enumerate(channels):
        ch_features = {
            "variance": float(variances[i]),
            "peak_to_peak": float(p2p[i]),
            "rms": float(rms[i]),
            "max_slope": float(max_slope[i])
        }
        
        # Add spectral blocks
        for band_name in BANDS.keys():
            ch_features[band_name] = float(band_powers[band_name][i])
            ch_features[f"relative_{band_name}"] = float(rel_band_powers[band_name][i])
            
        per_channel[ch_name] = ch_features

    # Global summaries
    global_summary = {}
    for band_name in BANDS.keys():
        global_summary[f"mean_{band_name}"] = float(np.mean(band_powers[band_name]))
        global_summary[f"mean_relative_{band_name}"] = float(np.mean(rel_band_powers[band_name]))
    
    # Global spatial ratios
    if frontal_indices and posterior_indices:
        f_delta = np.mean([rel_band_powers["delta"][idx] for idx in frontal_indices])
        p_delta = np.mean([rel_band_powers["delta"][idx] for idx in posterior_indices])
        global_summary["frontal_posterior_delta_ratio"] = float(f_delta / (p_delta + 1e-12))
        
    if left_indices and right_indices:
        l_power = np.mean([total_power[idx] for idx in left_indices])
        r_power = np.mean([total_power[idx] for idx in right_indices])
        global_summary["left_right_total_asymmetry"] = float(abs(l_power - r_power) / (l_power + r_power + 1e-12))

    return {
        "per_channel": per_channel,
        "global_summary": global_summary
    }
