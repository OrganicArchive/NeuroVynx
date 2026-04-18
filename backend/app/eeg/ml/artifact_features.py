import numpy as np
from typing import Dict, Any, List

FEATURE_SCHEMA_VERSION = "1.0-explainable-baseline"

def extract_artifact_features(data_uv: np.ndarray, sfreq: float, channels: List[str]) -> Dict[str, Any]:
    """
    Computes explainable engineered features for artifact classification.
    Focuses on time-domain and spectral-domain metrics that map directly 
    to physical concepts (e.g., muscle tension, eye movements).
    """
    features = {}
    
    # 1. Variance & Amplitude Metrics (Instability detection)
    features["global_variance"] = float(np.var(data_uv))
    features["mean_abs_amplitude"] = float(np.mean(np.abs(data_uv)))
    features["peak_to_peak"] = float(np.ptp(data_uv))
    
    # 2. Spectral Composition (HF for muscle, LF for blinks)
    # Using a simplified periodogram logic for feature vectors
    fft_vals = np.abs(np.fft.rfft(data_uv, axis=1))
    freqs = np.fft.rfftfreq(data_uv.shape[1], 1/sfreq)
    
    # High-Frequency Burden (EMG Proxy)
    hf_mask = (freqs >= 30.0) & (freqs <= 80.0)
    features["hf_power_mean"] = float(np.mean(fft_vals[:, hf_mask]))
    
    # Low-Frequency Burden (Eye Blink/Drift Proxy)
    lf_mask = (freqs >= 1.0) & (freqs <= 4.0)
    features["lf_power_mean"] = float(np.mean(fft_vals[:, lf_mask]))
    
    # LF/HF Ratio (Complexity proxy)
    if features["hf_power_mean"] > 0:
        features["lf_hf_ratio"] = features["lf_power_mean"] / features["hf_power_mean"]
    else:
        features["lf_hf_ratio"] = 0.0
        
    # 3. Channel Consistency (Electrode dropout detection)
    per_channel_var = np.var(data_uv, axis=1)
    features["channel_variance_std"] = float(np.std(per_channel_var))
    features["low_variance_channel_count"] = int(np.sum(per_channel_var < 0.1))
    
    # 4. Slope & Spikiness (Clipping/Impulse noise)
    diffs = np.diff(data_uv, axis=1)
    features["max_slope"] = float(np.max(np.abs(diffs)))
    features["mean_slope"] = float(np.mean(np.abs(diffs)))
    
    # Metadata for provenance
    features["schema_version"] = FEATURE_SCHEMA_VERSION
    
    return features

def get_feature_labels() -> List[str]:
    """Returns the list of engineered feature names for model training alignment."""
    return [
        "global_variance", "mean_abs_amplitude", "peak_to_peak",
        "hf_power_mean", "lf_power_mean", "lf_hf_ratio",
        "channel_variance_std", "low_variance_channel_count",
        "max_slope", "mean_slope"
    ]
