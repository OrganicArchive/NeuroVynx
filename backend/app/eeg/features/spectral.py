"""
NeuroVynx: Spectral Processing Engine
======================================

This module handles frequency-domain transformations of EEG signals.
It primary focus is calculating 'Brainwave Bands' (Delta, Theta, Alpha, Beta) 
to identify neurological states like focus, relaxation, or sleep.

Core Method: Welch's Periodogram
- We use the Welch method because it segments the data, reduces variance 
  of the spectral estimate, and is highly robust to noise transients.
"""

from typing import Tuple
import numpy as np
from scipy import signal

def compute_psd(data: np.ndarray, sfreq: float):
    """
    Computes the Power Spectral Density (PSD).
    
    We use a 2-second overlapping window (Hanning) to balance frequency 
    resolution and variance reduction.
    
    Args:
        data: Shape (n_channels, n_samples)
        sfreq: Sampling frequency in Hz.
    """
    # Define window size: sfreq * 2 gives 0.5Hz frequency resolution
    nperseg = int(min(sfreq * 2, data.shape[-1]))
    
    # signal.welch performs the FFT and averages the results
    freqs, psd = signal.welch(data, sfreq, nperseg=nperseg, axis=-1)
    return freqs, psd

def band_power(psd: np.ndarray, freqs: np.ndarray, band: tuple):
    """
    Calculates the Absolute Power (Area Under the Curve) for a frequency band.
    
    Args:
        psd: Power spectral density array.
        freqs: Corresponding frequency bins.
        band: (Low, High) frequency limits.
    """
    low, high = band
    # Find indices corresponding to the requested band using a half-open policy
    # (Except for a possible edge case at the very top of the intended spectrum)
    idx_band = np.logical_and(freqs >= low, freqs < high)
    
    # Calculate the frequency resolution (step size between bins)
    freq_res = freqs[1] - freqs[0]
    
    # --- INTEGRATION STEP ---
    # We approximate the definite integral of the PSD curve. 
    # Summing the PSD values and multiplying by freq_res gives the 
    # absolute power in microvolts squared (uV^2).
    bp = np.sum(psd[..., idx_band], axis=-1) * freq_res
    return bp

def relative_power(bp: np.ndarray, total_power: np.ndarray):
    """
    Normalizes power to a 0-1 range relative to the full spectrum.
    
    Relative power is often more informative than absolute power because 
    it accounts for skull thickness and electrode impedance variations 
    across different subjects.
    """
    # Prevents division-by-zero on flatlined hardware
    return bp / (total_power + 1e-12)

