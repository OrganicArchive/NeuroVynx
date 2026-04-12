import os
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional

from app.core.database import get_db
from app.models.session import Session
import mne
import numpy as np

router = APIRouter()

@router.get("/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "id": session.id,
        "filename": session.filename,
        "status": session.status,
        "created_at": session.created_at,
        "duration_seconds": session.duration_seconds
    }

@router.get("/{session_id}/segment")
def get_session_segment(
    session_id: str, 
    start: float = Query(0.0, description="Start time in seconds"),
    duration: float = Query(10.0, description="Duration in seconds"),
    apply_notch: bool = Query(False, description="Apply 50Hz notch filter"),
    apply_bandpass: bool = Query(False, description="Apply 1-45Hz bandpass filter"),
    db: DBSession = Depends(get_db)
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not os.path.exists(session.file_path):
        raise HTTPException(status_code=404, detail="Original EDF file not found on disk")

    try:
        # Load lazily to access metadata
        raw = mne.io.read_raw_edf(session.file_path, preload=False, verbose=False)
        sfreq = raw.info['sfreq']
        
        # Calculate sample indices
        start_samp = int(start * sfreq)
        stop_samp = int((start + duration) * sfreq)
        
        # Prevent out of bounds
        max_samp = int(raw.times[-1] * sfreq)
        start_samp = max(0, min(start_samp, max_samp))
        stop_samp = max(0, min(stop_samp, max_samp))
        
        # Extract and copy the requested slice into memory to safely apply filters
        raw_slice = raw.copy().crop(tmin=start_samp/sfreq, tmax=stop_samp/sfreq).load_data()
        
        # Apply DSP if requested
        if apply_notch:
            # Simple 50Hz notch filter
            raw_slice.notch_filter(freqs=50.0, verbose=False)
            
        if apply_bandpass:
            # Simple 1-45Hz bandpass
            raw_slice.filter(l_freq=1.0, h_freq=45.0, verbose=False)
            
        data = raw_slice.get_data()
        times = raw_slice.times + (start_samp/sfreq) # shift times back to absolute
        
        # Convert microvolts context. MNE internally stores as Volts.
        # We multiply by 1e6 to return microvolts (uV) usually preferred by viewers.
        data_uv = data * 1e6
        
        return {
            "session_id": session_id,
            "sample_rate": sfreq,
            "start_time": start,
            "duration": duration,
            "channels": raw_slice.ch_names,
            "times": times.tolist(),
            "data": data_uv.tolist() # Nested array: [channel_index][sample_index]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading EEG segment: {str(e)}")

from app.eeg.quality.engine import compute_segment_quality

@router.get("/{session_id}/quality")
def get_session_quality(
    session_id: str, 
    start: float = Query(0.0, description="Start time in seconds"),
    duration: float = Query(10.0, description="Duration in seconds"),
    context: str = Query("awake", description="Clinical context: 'awake' or 'sleep'"),
    db: DBSession = Depends(get_db)
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not os.path.exists(session.file_path):
        raise HTTPException(status_code=404, detail="Original EDF file not found on disk")

    try:
        raw = mne.io.read_raw_edf(session.file_path, preload=False, verbose=False)
        sfreq = raw.info['sfreq']
        
        start_samp = int(start * sfreq)
        stop_samp = int((start + duration) * sfreq)
        
        max_samp = int(raw.times[-1] * sfreq)
        start_samp = max(0, min(start_samp, max_samp))
        stop_samp = max(0, min(stop_samp, max_samp))
        
        raw_slice = raw.copy().crop(tmin=start_samp/sfreq, tmax=stop_samp/sfreq).load_data()
        
        data_uv = raw_slice.get_data() * 1e6
        
        # Run quality analysis
        analysis = compute_segment_quality(data_uv, raw_slice.ch_names, sfreq, context=context)
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing EEG quality: {str(e)}")

from app.eeg.features.engine import extract_features

@router.get("/{session_id}/features")
def get_session_features(
    session_id: str, 
    start: float = Query(0.0, description="Start time in seconds"),
    duration: float = Query(10.0, description="Duration in seconds"),
    apply_notch: bool = Query(False, description="Apply 50Hz notch filter"),
    apply_bandpass: bool = Query(False, description="Apply 1-45Hz bandpass filter"),
    db: DBSession = Depends(get_db)
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not os.path.exists(session.file_path):
        raise HTTPException(status_code=404, detail="Original EDF file not found on disk")

    try:
        raw = mne.io.read_raw_edf(session.file_path, preload=False, verbose=False)
        sfreq = raw.info['sfreq']
        
        start_samp = int(start * sfreq)
        stop_samp = int((start + duration) * sfreq)
        
        max_samp = int(raw.times[-1] * sfreq)
        start_samp = max(0, min(start_samp, max_samp))
        stop_samp = max(0, min(stop_samp, max_samp))
        
        raw_slice = raw.copy().crop(tmin=start_samp/sfreq, tmax=stop_samp/sfreq).load_data()
        
        if apply_notch:
            raw_slice.notch_filter(freqs=50.0, verbose=False)
            
        if apply_bandpass:
            raw_slice.filter(l_freq=1.0, h_freq=45.0, verbose=False)
            
        data_uv = raw_slice.get_data() * 1e6
        
        features = extract_features(data_uv, sfreq, raw_slice.ch_names)
        
        return {
            "window_start": start,
            "duration": duration,
            "sample_rate": sfreq,
            "per_channel": features["per_channel"],
            "global_summary": features["global_summary"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting features: {str(e)}")

from app.eeg.analysis.pipeline import analyze_window

@router.get("/{session_id}/analysis")
def get_session_analysis(
    session_id: str, 
    start: float = Query(0.0),
    duration: float = Query(10.0),
    apply_notch: bool = Query(False),
    apply_bandpass: bool = Query(False),
    context: str = Query("awake"),
    db: DBSession = Depends(get_db)
):
    """
    Primary Unified Analysis Endpoint.
    Returns synchronized Quality metrics, Spectral Features, and Baseline comparisons 
    for a specific 10-second slice. Supports dynamic clinical context (Awake/Sleep).
    """
    try:
        return analyze_window(
            db=db,
            session_id=session_id,
            start=start,
            duration=duration,
            apply_notch=apply_notch,
            apply_bandpass=apply_bandpass,
            include_quality=True,
            include_features=True,
            include_baseline=True,
            context=context
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")

@router.get("/{session_id}/report")
def export_session_report(
    session_id: str,
    apply_notch: bool = Query(False),
    apply_bandpass: bool = Query(False),
    db: DBSession = Depends(get_db)
):
    """
    Generates a full structured report for the entire session.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        # We run the analysis pipeline over the entire file
        # Note: For massive files this might be slow, but it's okay for MVP
        report = analyze_window(
            db=db,
            session_id=session_id,
            start=0.0,
            duration=session.duration_seconds,
            apply_notch=apply_notch,
            apply_bandpass=apply_bandpass,
            include_quality=True,
            include_features=True,
            include_baseline=True
        )
        
        # Strip out the raw nested arrays from the 'window' key to keep the JSON report small
        if "window" in report and "data" in report["window"]:
            del report["window"]["data"]
            
        return {
            "metadata": {
                "session_id": session.id,
                "filename": session.filename,
                "total_duration": session.duration_seconds,
                "report_generated_at": str(os.popen("date").read().strip() if os.name != 'nt' else "now")
            },
            "dsp_settings": {
                "notch_50hz": apply_notch,
                "bandpass_1_45hz": apply_bandpass
            },
            "analysis": report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating full report: {str(e)}")

from app.eeg.analysis.timeline import scan_session_timeline

@router.get("/{session_id}/timeline")
def get_session_timeline(
    session_id: str,
    window: float = Query(10.0),
    step: float = Query(5.0),
    apply_notch: bool = Query(True),
    apply_bandpass: bool = Query(True),
    db: DBSession = Depends(get_db)
):
    """
    Scans the session via sliding windows to produce a compact Artifact Minimap JSON.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        return scan_session_timeline(
            file_path=session.file_path,
            total_duration=session.duration_seconds,
            window=window,
            step=step,
            apply_notch=apply_notch,
            apply_bandpass=apply_bandpass
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeline scan error: {str(e)}")
