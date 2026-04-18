import mne
import numpy as np
from typing import List
import os

def create_synthetic_signal(
    name: str,
    duration: float = 10.0,
    sfreq: float = 250.0,
    ch_names: list = None,
    delta_amp: float = 0.0,
    theta_amp: float = 0.0,
    alpha_amp: float = 10.0, 
    beta_amp: float = 5.0,
    blink_amp: float = 0.0,
    line_noise_amp: float = 0.0,
    noise_floor: float = 2.0
):
    if ch_names is None:
        ch_names = ["FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2"]
    
    n_samples = int(duration * sfreq)
    times = np.arange(n_samples) / sfreq
    
    data = np.zeros((len(ch_names), n_samples))
    
    for i, ch in enumerate(ch_names):
        data[i] += np.random.normal(0, noise_floor, n_samples)
        data[i] += alpha_amp * np.sin(2 * np.pi * 10.0 * times)
        data[i] += delta_amp * np.sin(2 * np.pi * 2.0 * times)
        data[i] += theta_amp * np.sin(2 * np.pi * 6.0 * times)
        data[i] += beta_amp * np.sin(2 * np.pi * 22.0 * times)
        
        # Artifacts
        if ch in ["FP1", "FP2"] and blink_amp > 0:
            for start_sec in [2.5, 5.5, 8.5]:
                start_idx = int(start_sec * sfreq)
                # INSTANT TRANSITION (to trigger diffs > 30)
                # Rise in 1 sample, fall in 100
                data[i, start_idx:start_idx+1] = blink_amp
                data[i, start_idx+1:start_idx+101] = np.linspace(blink_amp, 0, 100)
                
        if line_noise_amp > 0:
            # We add enough to trigger 'Broadband' but not 'Fatal'
            data[i] += line_noise_amp * np.sin(2 * np.pi * 50.0 * times)

    # Convert to Volts
    data_v = data * 1e-6
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types="eeg")
    raw = mne.io.RawArray(data_v, info, verbose=False)
    return raw

def generate_benchmark_suite(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    
    cases = {
        "case_a_clean": {"alpha_amp": 25.0, "noise_floor": 2.0},
        "case_b_blinks": {"alpha_amp": 10.0, "blink_amp": 400.0, "noise_floor": 4.0}, 
        "case_c_line_noise": {"alpha_amp": 10.0, "line_noise_amp": 80.0}, # Strong line noise
        "case_d_unstable": {"noise_floor": 10.0}, 
        "case_e_diffuse_slowing": {"delta_amp": 45.0, "theta_amp": 35.0, "alpha_amp": 2.0},
        "case_f_alpha_reduction": {"alpha_amp": 0.5, "beta_amp": 15.0, "theta_amp": 10.0},
        "case_g_mixed": {"theta_amp": 15.0, "blink_amp": 200.0, "line_noise_amp": 30.0}
    }
    
    for filename, params in cases.items():
        raw = create_synthetic_signal(name=filename, **params)
        raw.export(os.path.join(output_dir, f"{filename}.edf"), overwrite=True, verbose=False)
        print(f"Verified {filename}.edf")

if __name__ == "__main__":
    generate_benchmark_suite("backend/tests/fixtures/validation_cases")

