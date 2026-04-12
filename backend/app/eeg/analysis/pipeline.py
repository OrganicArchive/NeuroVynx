"""
NeuroVynx: Unified Analysis Pipeline
====================================

This module acts as the orchestrator for the backend. It coordinates file I/O, 
Digital Signal Processing (DSP) filter applications, and the various 
analytical engines (Quality, Features, Baselines).

The pipeline is designed to be entirely stateless, processing lazy-loaded 
slices of raw binary data on-demand.
"""

import os
import mne
from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.eeg.quality.engine import compute_segment_quality
from app.eeg.features.engine import extract_features
from app.eeg.baselines.repository import load_baseline
from app.eeg.baselines.engine import compare_to_baseline

def analyze_window(
    db: DBSession,
    session_id: str,
    start: float,
    duration: float,
    apply_notch: bool = False,
    apply_bandpass: bool = False,
    include_quality: bool = True,
    include_features: bool = True,
    include_baseline: bool = True,
    user_id: str = "default_user",
    baseline_type: str = "resting",
    context: str = "awake"
):
    """
    Executes a high-resolution analysis of a specific EEG time window.
    
    This function performs the following steps:
    1. Lazy-loads a slice of data from the raw EDF/BDF file.
    2. Applies optional DSP filters (Notch, Bandpass).
    3. Runs the Heuristic Quality Engine.
    4. Computes Power Spectral Density (PSD) features.
    5. (Optional) Performs deviation analysis against a user's baseline profile.
    
    Args:
        db: SQLAlchemy database session.
        session_id: Unique ID of the recording session.
        start: Start time in seconds.
        duration: Window duration in seconds (typically 10s).
    """
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not os.path.exists(db_session.file_path):
        raise HTTPException(status_code=404, detail="Original EDF file not found on disk")

    try:
        # --- 1. LAZY LOADING ---
        # We use preload=False to avoid loading the entire file into RAM.
        # This allows NeuroVynx to handle multi-gigabyte files with constant memory usage.
        raw = mne.io.read_raw_edf(db_session.file_path, preload=False, verbose=False)
        
        # CLEANUP: Strip trailing dots often found in standardized EDF exports
        raw.rename_channels(lambda ch: ch.strip('.'))
        
        sfreq = raw.info['sfreq']
        
        # Calculate samples carefully based on sfreq
        start_samp = int(start * sfreq)
        stop_samp = int((start + duration) * sfreq)
        max_samp = int(raw.times[-1] * sfreq)
        
        # Safety bounds to prevent MNE array indexing errors
        start_samp = max(0, min(start_samp, max_samp))
        stop_samp = max(0, min(stop_samp, max_samp))
        
        # Load only the requested slice into memory
        raw_slice = raw.copy().crop(tmin=start_samp/sfreq, tmax=stop_samp/sfreq).load_data()
        
        # --- 2. ONLINE DSP FILTERS ---
        # Notch filter removes specific frequency interference (typically 50/60Hz AC noise).
        if apply_notch:
            raw_slice.notch_filter(freqs=50.0, verbose=False)
            
        # Bandpass filter (1-45Hz) isolates standard neurological frequency bands.
        if apply_bandpass:
            raw_slice.filter(l_freq=1.0, h_freq=45.0, verbose=False)
            
        # Convert to microvolts (uV) for human-readable consistency in the UI
        data_uv = raw_slice.get_data() * 1e6
        channels = raw_slice.ch_names
        
        result = {
            "window": {
                "start": start,
                "duration": duration,
                "sample_rate": sfreq,
                "channels": channels,
                "data": data_uv.tolist() # include for trace rendering
            }
        }
        
        # --- 3. MODULAR ANALYSIS MODULES ---
        
        # Signal Quality: Checks for artifacts and channel drops
        if include_quality:
            result["quality"] = compute_segment_quality(data_uv, channels, sfreq, context=context)
            
            # --- DIAGNOSTIC ISOLATION CHECK ---
            # Verified channel separation and penalty scaling
            if "debug_isolation_check" in result["quality"]:
                debug = result["quality"]["debug_isolation_check"]
                print(f"\n[DIAGNOSTIC] Channel Isolation Check - Window {start}s")
                print(f"  - EEG Channels ({len(debug['eeg_channels_used'])}): {debug['eeg_channels_used']}")
                print(f"  - EOG Channels ({len(debug['eog_channels_used'])}): {debug['eog_channels_used']}")
                print(f"  - Aux Sensors Excluded: {debug['aux_channels_excluded']}")
                print(f"  - EEG Score (Raw): {debug['eeg_score_raw']}%")
                print(f"  - EEG Total Penalty: -{debug['eeg_penalty_total']:.1f} pts (Scaled x0.8)")
                print(f"  - Final EEG Quality: {debug['eeg_score_final']}%")
                print(f"  - Soft Protection Active: {debug['soft_protection_active']}")
                print("-" * 50)
            
        # Features: Computes absolute and relative band power using Welch's method.
        if include_features:
            features = extract_features(data_uv, sfreq, channels)
            result["features"] = features
            
            # Baseline Comparison: Direct comparison to a stored resting/calibration record.
            # This allows the UI to highlight deviations (e.g., '140% of baseline delta').
            if include_baseline:
                baseline_obj = load_baseline(db, user_id, baseline_type)
                if baseline_obj:
                    result["baseline_comparison"] = compare_to_baseline(features, baseline_obj.features)
                else:
                    result["baseline_comparison"] = {"error": "No baseline configured"}

        return result
        
    except Exception as e:
        # Surface internal errors gracefully with meaningful details
        raise HTTPException(status_code=500, detail=f"Error executing analysis pipeline: {str(e)}")
