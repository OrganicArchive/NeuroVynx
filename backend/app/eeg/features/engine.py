from typing import List, Optional
import numpy as np
from app.eeg.features import spectral
from app.eeg.config.analysis_standards import (
    CANONICAL_BANDS, TOTAL_POWER_RANGE, REGION_MAPPING, 
    clean_name, get_region_for_channel, EPSILON
)

def extract_features(data_uv: np.ndarray, sfreq: float, channels: list):
    """
    Extracts features for an N-channel EEG segment.
    data_uv: numpy array of shape (n_channels, n_samples)
    """
    n_channels, n_samples = data_uv.shape
    
    # 1. Compute PSD efficiently vectorized across all channels
    freqs, psd = spectral.compute_psd(data_uv, sfreq)
    
    # Standard 0.5 - 30.0 Hz total power for relative denominator
    total_power_30 = spectral.band_power(psd, freqs, TOTAL_POWER_RANGE)
    
    # Optional High-Frequency / EMG Proxy (30 - 45 Hz) - Kept separate from canonical relative power
    hf_abs_power = spectral.band_power(psd, freqs, (30.0, 45.0))
    
    # Pre-calculate band powers for all channels simultaneously
    band_powers = {}
    rel_band_powers = {}
    for band_name, freq_range in CANONICAL_BANDS.items():
        bp = spectral.band_power(psd, freqs, freq_range)
        band_powers[band_name] = bp
        # Canonical relative power (0.5-30Hz base)
        rel_band_powers[band_name] = bp / (total_power_30 + EPSILON)
        
    # Time-domain features
    variances = np.var(data_uv, axis=1)
    p2p = np.ptp(data_uv, axis=1)
    rms = np.sqrt(np.mean(np.square(data_uv), axis=1))
    max_slope = np.max(np.abs(np.diff(data_uv, axis=1)), axis=1)
    
    # Regional classification using standardized standards
    region_indices = {region: [] for region in REGION_MAPPING.keys()}
    for i, ch in enumerate(channels):
        region = get_region_for_channel(ch)
        if region in region_indices:
            region_indices[region].append(i)

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
        for band_name in CANONICAL_BANDS.keys():
            ch_features[band_name] = float(band_powers[band_name][i])
            ch_features[f"relative_{band_name}"] = float(rel_band_powers[band_name][i])
            
        # Add high-frequency / EMG proxy separately
        ch_features["hf_abs_power"] = float(hf_abs_power[i])
            
        per_channel[ch_name] = ch_features

    # Global summaries
    # FIX: Use 'Ratio of Means' (Ratio of average Absolute power) for cross-layer agreement.
    global_summary = {}
    
    # Calculate global mean total power (0.5 - 30.0 Hz range)
    avg_total_power_30 = np.mean(total_power_30)
    
    for band_name in CANONICAL_BANDS.keys():
        avg_abs_band = np.mean(band_powers[band_name])
        global_summary[f"mean_{band_name}"] = float(avg_abs_band)
        
        # Correct global relative power aggregation (Ratio of Means)
        rel_global = avg_abs_band / (avg_total_power_30 + EPSILON)
        global_summary[f"mean_relative_{band_name}"] = float(rel_global)
    
    # Global spatial ratios (Frontal-Posterior)
    # Based on standardized region mapping.
    f_indices = region_indices.get("Frontal", [])
    p_indices = region_indices.get("Occipital", []) # Occipital is the primary posterior anchor
    
    if f_indices and p_indices:
        f_delta = np.mean([rel_band_powers["delta"][idx] for idx in f_indices])
        p_delta = np.mean([rel_band_powers["delta"][idx] for idx in p_indices])
        global_summary["frontal_posterior_delta_ratio"] = float(f_delta / (p_delta + EPSILON))
        
    # Global left-right asymmetry
    left_indices = []
    right_indices = []
    for i, ch in enumerate(channels):
        name = clean_name(ch)
        import re
        num_match = re.search(r'\d+', name)
        if num_match:
            if int(num_match.group()) % 2 != 0: left_indices.append(i)
            else: right_indices.append(i)
            
    if left_indices and right_indices:
        l_power = np.mean([total_power_30[idx] for idx in left_indices])
        r_power = np.mean([total_power_30[idx] for idx in right_indices])
        global_summary["left_right_total_asymmetry"] = float(abs(l_power - r_power) / (l_power + r_power + EPSILON))

    return {
        "per_channel": per_channel,
        "global_summary": global_summary
    }


