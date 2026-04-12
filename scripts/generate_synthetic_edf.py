import mne
import numpy as np
import os
from pathlib import Path

def generate_synthetic_edf(filename, duration=60, sfreq=256, scenario="normal"):
    """
    Generates a synthetic EEG EDF file for testing.
    Scenarios: 'normal', 'blinks', 'noisy', 'line_noise'
    """
    # Define channels (10-20 system)
    ch_names = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2']
    n_channels = len(ch_names)
    n_samples = duration * sfreq
    times = np.arange(n_samples) / sfreq
    
    # Initialize empty data array (in Volts, MNE default)
    data = np.zeros((n_channels, n_samples))
    
    # 1. Add background Pink Noise (1/f) to all channels
    for i in range(n_channels):
        # Generate white noise and scale by 1/f in frequency domain
        white_noise = np.random.normal(0, 10e-6, n_samples)
        freqs = np.fft.rfftfreq(n_samples, d=1/sfreq)
        # Avoid division by zero
        freqs[0] = freqs[1]
        scaling = 1.0 / np.sqrt(freqs)
        noise_fft = np.fft.rfft(white_noise) * scaling
        data[i] = np.fft.irfft(noise_fft, n=n_samples)

    # 2. Add Alpha Rhythm (10Hz) to Posterior channels (O1, O2)
    if "normal" in scenario or "blinks" in scenario:
        alpha_amp = 30e-6 # 30 uV
        for ch_idx in [8, 9]: # O1, O2
            data[ch_idx] += alpha_amp * np.sin(2 * np.pi * 10 * times)

    # 3. Scenario Specifics
    if scenario == "blinks":
        # Add high-amplitude delta waves in frontal channels every 5-8 seconds
        blink_amp = 150e-6 # 150 uV
        for t_start in range(5, duration, 7):
            idx_start = int(t_start * sfreq)
            idx_end = int((t_start + 0.5) * sfreq)
            dur = idx_end - idx_start
            blink_wave = blink_amp * np.sin(np.pi * np.arange(dur) / dur)
            data[0, idx_start:idx_end] += blink_wave # Fp1
            data[1, idx_start:idx_end] += blink_wave # Fp2

    elif scenario == "noisy":
        # Add high-frequency jitter (Muscle artifact simulation)
        for i in range(n_channels):
            data[i] += np.random.normal(0, 40e-6, n_samples)

    elif scenario == "line_noise":
        # Add 50Hz sine wave (AC interference)
        line_amp = 50e-6 # 50 uV
        for i in range(n_channels):
            data[i] += line_amp * np.sin(2 * np.pi * 50 * times)

    # Create MNE info and raw object
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types='eeg')
    raw = mne.io.RawArray(data, info)
    
    # Add standard montage
    montage = mne.channels.make_standard_montage('standard_1020')
    raw.set_montage(montage)

    # Save to EDF
    # MNE's export requires pyedflib
    try:
        from mne.export import export_raw
        export_raw(filename, raw, fmt='edf', overwrite=True)
        print(f"Successfully generated: {filename}")
    except Exception as e:
        print(f"Error exporting to EDF: {e}")

if __name__ == "__main__":
    output_dir = Path("data/synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scenarios = [
        ("synthetic_normal.edf", "normal"),
        ("synthetic_blinks.edf", "blinks"),
        ("synthetic_noisy.edf", "noisy"),
        ("synthetic_line_noise.edf", "line_noise")
    ]
    
    for fname, scen in scenarios:
        generate_synthetic_edf(output_dir / fname, scenario=scen)
