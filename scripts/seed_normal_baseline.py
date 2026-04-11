import requests
import sys
import json

def seed_normal_baseline(session_id):
    """
    Injects a synthetic 'Normal Adult (Eyes Closed)' baseline profile 
    for the given session ID.
    """
    url = "http://localhost:8000/api/v1/baselines/create"
    
    # Standardised Normal Profile (Relative Powers)
    # Alpha-dominant (Eyes Closed) resting state
    normal_features = {
        "global_summary": {
            "mean_delta": 2.5,
            "mean_relative_delta": 0.05,
            "mean_theta": 5.0,
            "mean_relative_theta": 0.10,
            "mean_alpha": 22.0,
            "mean_relative_alpha": 0.45,
            "mean_beta": 8.0,
            "mean_relative_beta": 0.15
        },
        "per_channel": {
            # Placeholder to satisfy structural checks
            "C3": {"peak_to_peak": 50.0, "alpha": 20.0, "relative_alpha": 0.4},
            "C4": {"peak_to_peak": 50.0, "alpha": 20.0, "relative_alpha": 0.4},
            "P3": {"peak_to_peak": 55.0, "alpha": 30.0, "relative_alpha": 0.5},
            "P4": {"peak_to_peak": 55.0, "alpha": 30.0, "relative_alpha": 0.5},
            "O1": {"peak_to_peak": 60.0, "alpha": 35.0, "relative_alpha": 0.6},
            "O2": {"peak_to_peak": 60.0, "alpha": 35.0, "relative_alpha": 0.6}
        }
    }

    metadata = {
        "label": "Synthetic Normal (Eyes Closed)",
        "timestamp": "2026-04-11T17:00:00Z",
        "data_sfreq": 160,
        "notes": "Standardized profile for testing NeuroVynx deviation analytics."
    }

    payload = {
        "session_id": session_id,
        "baseline_type": "resting",
        "features": normal_features,
        "metadata": metadata
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"\n[SUCCESS] Normal Baseline Injected for Session: {session_id}")
        print(f"Server response: {response.json()}")
    except Exception as e:
        print(f"\n[ERROR] Failed to seed baseline: {e}")
        print("Make sure the NeuroVynx backend is running (run_NeuroVynx.bat)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_normal_baseline.py <session_id>")
    else:
        seed_normal_baseline(sys.argv[1])
