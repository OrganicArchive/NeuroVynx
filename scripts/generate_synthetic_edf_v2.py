import mne
import numpy as np
import os
from pathlib import Path

def generate_synthetic_edf(filename, duration=60, sfreq=256, scenario="normal"):
    """
    Generates a more 'organic' synthetic EEG EDF file.
    Changes:
    - Unique noise per channel to prevent MAD=0 errors.
    - Distributed alpha (global weak 10Hz, strong posterior).
    - Reduced Delta floor for clearer spectral features.
    """
    ch_names = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2']
    n_channels = len(ch_names)
    n_samples = duration * sfreq
    times = np.arange(n_samples) / sfreq
    
    data = np.zeros((n_channels, n_samples))
    
    # 1. Add Unique background noise per channel (Organic var)
    for i in range(n_channels):
        # Slightly different noise amplitudes per channel (5uV to 15uV)
        base_noise_amp = np.random.uniform(5e-6, 15e-6)
        white_noise = np.random.normal(0, base_noise_amp, n_samples)
        
        freqs = np.fft.rfftfreq(n_samples, d=1/sfreq)
        freqs[0] = freqs[1]
        # Use a steeper 1/f roll-off to keep Delta in check
        scaling = 1.0 / (freqs ** 0.8) 
        noise_fft = np.fft.rfft(white_noise) * scaling
        data[i] = np.fft.irfft(noise_fft, n=n_samples)

    # 2. Add Alpha Rhythm (10Hz) - Scaled across head
    if scenario in ["normal", "blinks"]:
        for i, ch in enumerate(ch_names):
            # Strong posterior (O1, O2), weak elsewhere
            is_occipital = ch in ['O1', 'O2']
            amp = 35e-6 if is_occipital else 8e-6
            # Add phase jitter to make it look less like a computer-generated sine wave
            phase = np.random.uniform(0, 2*np.pi)
            data[i] += amp * np.sin(2 * np.pi * 10 * times + phase)

    # 3. Scenario Specifics
    if scenario == "blinks":
        blink_amp = 180e-6 
        for t_start in range(5, duration, 8):
            idx_start = int(t_start * sfreq)
            dur_samples = int(0.4 * sfreq)
            idx_end = idx_start + dur_samples
            # Half-sine pulse
            blink_wave = blink_amp * np.sin(np.pi * np.arange(dur_samples) / dur_samples)
            # Frontal only
            data[0, idx_start:idx_end] += blink_wave 
            data[1, idx_start:idx_end] += blink_wave

    elif scenario == "noisy":
        # Add high-frequency technical jitter
        for i in range(n_channels):
            data[i] += np.random.normal(0, 50e-6, n_samples)

    elif scenario == "line_noise":
        line_amp = 60e-6 
        for i in range(n_channels):
            data[i] += line_amp * np.sin(2 * np.pi * 50 * times)

    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types='eeg')
    raw = mne.io.RawArray(data, info)
    
    montage = mne.channels.make_standard_montage('standard_1020')
    raw.set_montage(montage)

    try:
        from mne.export import export_raw
        export_raw(filename, raw, fmt='edf', overwrite=True)
        print(f"Successfully generated: {filename}")
    except Exception as e:
        print(f"Error exporting to EDF: {e}")

if __name__ == "__main__":
    output_dir = Path("data/improved_synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scenarios = [
        ("synthetic_normal_v2.edf", "normal"),
        ("synthetic_blinks_v2.edf", "blinks"),
        ("synthetic_noisy_v2.edf", "noisy"),
        ("synthetic_line_noise_v2.edf", "line_noise")
    ]
    
    for fname, scen in scenarios:
        generate_synthetic_edf(output_dir / fname, scenario=scen)
