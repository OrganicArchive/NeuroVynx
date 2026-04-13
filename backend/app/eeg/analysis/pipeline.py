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
from app.eeg.qeeg.engine import compute_qeeg_layer
from app.eeg.qeeg.temporal import compute_temporal_qeeg
from app.eeg.qeeg.topography import compute_band_topographies, compute_normative_topography
from app.eeg.qeeg.normative import compute_normative_comparison
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
    context: str = "awake",
    age: Optional[int] = None,
    age_band: Optional[str] = None
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
        # --- 0. FILE INITIALIZATION ---
        # We use preload=False to avoid loading the entire file into RAM.
        raw = mne.io.read_raw_edf(db_session.file_path, preload=False, verbose=False)
        
        # CLEANUP: Strip trailing dots often found in standardized EDF exports
        raw.rename_channels(lambda ch: ch.strip('.'))
        
        sfreq = raw.info['sfreq']
        max_time = raw.times[-1]

        # --- 1. CONTEXT LOADING ---
        # We load the current window PLUS 120s of preceding context for temporal analysis
        context_duration = 120.0
        total_start = max(0, start - context_duration)
        total_end = start + duration
        
        # Safety bounds
        total_start = max(0, min(total_start, max_time))
        total_end = max(0, min(total_end, max_time))
        
        # Load the combined slice
        raw_combined = raw.copy().crop(tmin=total_start, tmax=total_end).load_data()
        
        # Apply DSP to the combined slice (improves filter stability)
        if apply_notch:
            raw_combined.notch_filter(freqs=50.0, verbose=False)
        if apply_bandpass:
            raw_combined.filter(l_freq=1.0, h_freq=45.0, verbose=False)
            
        # Get data and convert to uV
        full_data_uv = raw_combined.get_data() * 1e6
        channels = raw_combined.ch_names
        
        # Identify current window indices within the combined slice
        # The current window starts at 'start' which is 'start - total_start' relative to slice
        current_rel_start = start - total_start
        curr_start_idx = int(current_rel_start * sfreq)
        curr_stop_idx = int((current_rel_start + duration) * sfreq)
        
        # Squeeze in edges if indexing jitter occurs
        curr_stop_idx = min(curr_stop_idx, full_data_uv.shape[1])
        data_uv = full_data_uv[:, curr_start_idx:curr_stop_idx]
        
        result = {
            "window": {
                "start": start,
                "duration": duration,
                "sample_rate": sfreq,
                "channels": channels,
                "data": data_uv.tolist() 
            }
        }
        
        # --- 3. MODULAR ANALYSIS MODULES ---
        
        # Signal Quality: Checks for artifacts and channel drops
        if include_quality:
            result["quality"] = compute_segment_quality(data_uv, channels, sfreq, context=context)
            
            # --- CONFIDENCE & DIAGNOSTIC LOGGING ---
            q = result["quality"]
            if "confidence_details" in q:
                conf = q["confidence_details"]
                print(f"\n[DIAGNOSTIC] Quality & Confidence Check - Window {start}s")
                print(f"  - EEG Quality: {q['eeg_quality_score']}%")
                print(f"  - Confidence: {q['confidence_score']}% ({q['confidence_level'].upper()})")
                print(f"  - Components: Cov={conf['components']['coverage']} Agr={conf['components']['agreement']} Cons={conf['components']['consistency']} Ctx={conf['components']['context']} Prot={conf['components']['protection']}")
                print(f"  - Reasoning: {', '.join(conf['reasons'])}")
                if conf['coverage_capped']:
                    print(f"  - [NOTICE] Low-coverage cap applied (Active EEG: {conf['active_eeg_channels']}/{conf['expected_eeg_channels']})")
                print("-" * 50)
            
            # --- 6. qEEG LAYER ---
            # Quantitative EEG metrics gated by Quality/Confidence
            result["qeeg"] = compute_qeeg_layer(
                data_uv=data_uv,
                channels=channels,
                sfreq=sfreq,
                quality_info=result["quality"],
                confidence_info=result["quality"].get("confidence_details", {})
            )
            
            # --- 7. TEMPORAL DYNAMICS ---
            # Retrospectively analyze the last 12 windows for trends
            history_results = []
            step = 10.0
            
            # We iterate backwards from start-10s
            t_back = start - step
            while t_back >= total_start and (start - t_back) <= 120.0:
                rel_t = t_back - total_start
                h_start_idx = int(rel_t * sfreq)
                h_stop_idx = int((rel_t + step) * sfreq)
                h_stop_idx = min(h_stop_idx, full_data_uv.shape[1])
                
                h_data = full_data_uv[:, h_start_idx:h_stop_idx]
                
                # Analyze this history window
                h_qual = compute_segment_quality(h_data, channels, sfreq, context=context)
                
                # Check inclusion thresholds for temporal analysis:
                # EEG Quality >= 50 and Confidence >= 50
                if h_qual.get("eeg_quality_score", 0) >= 50 and h_qual.get("confidence_score", 0) >= 50:
                    h_qeeg = compute_qeeg_layer(
                        data_uv=h_data,
                        channels=channels,
                        sfreq=sfreq,
                        quality_info=h_qual,
                        confidence_info=h_qual.get("confidence_details", {})
                    )
                    # Only include if actually available
                    if h_qeeg["is_available"]:
                        history_results.insert(0, h_qeeg)
                
                t_back -= step
                
            result["temporal_qeeg"] = compute_temporal_qeeg(
                history=history_results,
                current_qeeg=result["qeeg"],
                window_step=step
            )

            # --- 8. SPATIAL TOPOGRAPHY ---
            # Generate 2D scalp maps from eligible EEG channels
            result["topography"] = compute_band_topographies(
                channel_metrics=result["qeeg"].get("channel_metrics", []),
                qeeg_trust_level=result["qeeg"].get("trust_level", "unavailable")
            )

            # --- 9. NORMATIVE COMPARISON (Phase 3A) ---
            # Compare metrics against references (Trust-gated internally)
            result["normative"] = compute_normative_comparison(
                qeeg_results=result["qeeg"],
                age=age,
                age_band=age_band,
                context=context
            )

            # --- 10. NORMATIVE TOPOGRAPHY (Phase 3B) ---
            # Generate deviation scalp maps (Symmetric z-score interpolation)
            result["normative_topography"] = compute_normative_topography(
                normative_layer=result["normative"],
                qeeg_trust_level=result["qeeg"].get("trust_level", "unavailable")
            )

            # [DIAGNOSTIC] qEEG Log
            qeeg = result["qeeg"]
            if qeeg["is_available"]:
                summary = qeeg["summary"]
                print(f"[DIAGNOSTIC] qEEG Summary - Window {start}s")
                print(f"  - Trust Level: {qeeg['trust_level'].upper()}")
                print(f"  - Eligible EEG: {qeeg['eligible_eeg_channels']}/{len(channels)}")
                print(f"  - Excluded EEG: {qeeg['excluded_eeg_channels']}")
                print(f"  - Dominant Band: {summary['dominant_global_band'].upper()}")
                print(f"  - Asymmetry Pairs: {len(qeeg['asymmetry_metrics'])}")
                
                # [DIAGNOSTIC] Temporal Log
                t_qeeg = result.get("temporal_qeeg", {})
                if t_qeeg.get("is_available"):
                    print(f"  - Temporal Stability: {t_qeeg['summary']['overall_stability'].upper()}")
                    print(f"  - Pattern Hint: {t_qeeg['summary']['dominant_temporal_pattern']}")
                
                # [DIAGNOSTIC] Topography Log
                topo = result.get("topography", {})
                if topo.get("is_available"):
                    print(f"  - Topography Coverage: {topo['eligible_channel_count']} channels ({topo['distinct_region_count']} regions)")
                    print(f"  - Strongest Region: {topo['summary']['strongest_region'].upper()}")
                else:
                    print(f"  - Topography Unavailable: {topo.get('reason', 'N/A')}")
                
                # [DIAGNOSTIC] Normative Log
                norm = result.get("normative", {})
                if norm.get("normative_allowed"):
                    print(f"  - Normative Results: {norm['normative_status'].upper()}")
                    print(f"  - Pattern: {norm['summary']['pattern_hint']}")
                else:
                    print(f"  - Normative Withheld: {norm.get('normative_status', 'N/A')}")
                
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
