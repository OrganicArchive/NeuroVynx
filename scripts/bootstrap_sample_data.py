import os
import urllib.request
import argparse
from pathlib import Path

# We download a sample EDF file directly if MNE is not yet installed or we just want
# a raw small EDF. The PhysioNet EEG Motor Movement/Imagery Dataset has small EDF files.
# We'll grab subject 1, run 1 (baseline eyes open).

EDF_URL = "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R01.edf"
DATA_DIR = Path(__file__).parent.parent / "data" / "sample"

def download_sample_data():
    """Downloads a public sample EDF dataset from PhysioNet for local testing."""
    print("Initializing sample dataset bootstrap...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = "test_eyes_open.edf"
    filepath = DATA_DIR / filename
    
    if filepath.exists():
        print(f"Sample data already exists at {filepath}")
        return

    print(f"Downloading sample EDF file from {EDF_URL}...")
    try:
        urllib.request.urlretrieve(EDF_URL, filepath)
        print(f"Successfully downloaded sample data to {filepath}")
    except Exception as e:
        print(f"Failed to download data: {e}")

if __name__ == "__main__":
    download_sample_data()
