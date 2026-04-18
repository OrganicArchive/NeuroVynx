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
from typing import Optional, List, Dict

from app.models.session import Session
from app.eeg.quality.engine import compute_segment_quality
from app.eeg.qeeg.engine import compute_qeeg_layer
from app.eeg.qeeg.temporal import compute_temporal_qeeg
from app.eeg.qeeg.topography import compute_band_topographies, compute_normative_topography
from app.eeg.qeeg.normative import compute_normative_comparison
from app.eeg.features.engine import extract_features
from app.eeg.baselines.repository import load_baseline
from app.eeg.baselines.engine import compare_to_baseline
from app.eeg.qeeg.interpretation.engine import run_interpretation
from app.eeg.ml.artifact_inference import run_ml_advisory
from app.utils.paths import ensure_valid_path
from .analysis_cache import get_cached_metadata, set_cached_metadata, get_cached_spectral, set_cached_spectral
from app.eeg.utils.performance_profiler import profile_function, profile_block
from app.plugins.manager import manager


@profile_function("Full Analysis Pipeline")
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
    age_band: Optional[str] = None,
    research_mode: bool = False,
    comparison_target: Optional[Dict] = None,
    quality_override: Optional[Dict] = None
):
    """
    Executes a high-resolution analysis of a specific EEG time window.
    Now supports Phase 3 Temporal Persistence and Longitudinal Comparison.
    """
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Apply self-healing path logic for machine portability
    file_path = ensure_valid_path(db_session.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original EDF file not found on disk")

    try:
        # --- 0. FILE INITIALIZATION ---
        raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
        raw.rename_channels(lambda ch: ch.strip('.'))
        
        meta = get_cached_metadata(file_path)
        if meta:
            sfreq = meta["sfreq"]
            max_time = meta["max_time"]
            raw_info = meta["raw_info"]
        else:
            sfreq = raw.info['sfreq']
            max_time = raw.times[-1]
            raw_info = {"ch_names": raw.ch_names}
            set_cached_metadata(file_path, {"sfreq": sfreq, "max_time": max_time, "raw_info": raw_info})

        # --- 1. CONTEXT LOADING ---
        context_duration = 120.0
        total_start = max(0, start - context_duration)
        total_end = start + duration
        total_start = max(0, min(total_start, max_time))
        total_end = max(0, min(total_end, max_time))
        
        raw_combined = raw.copy().crop(tmin=total_start, tmax=total_end).load_data()
        
        if apply_notch:
            raw_combined.notch_filter(freqs=50.0, verbose=False)
        if apply_bandpass:
            raw_combined.filter(l_freq=1.0, h_freq=45.0, verbose=False)
            
        full_data_uv = raw_combined.get_data() * 1e6
        channels = raw_combined.ch_names
        
        current_rel_start = start - total_start
        curr_start_idx = int(current_rel_start * sfreq)
        curr_stop_idx = int((current_rel_start + duration) * sfreq)
        curr_stop_idx = min(curr_stop_idx, full_data_uv.shape[1])
        data_uv = full_data_uv[:, curr_start_idx:curr_stop_idx]
        
        result = {
            "window": {
                "start": start,
                "duration": duration,
                "sample_rate": sfreq,
                "channels": channels,
                "data": data_uv.tolist() 
            },
            "plugin_results": [],
            "preprocessing": {
                "filtering_applied": apply_notch or apply_bandpass,
                "applied_notch_freq": 50.0 if apply_notch else None,
                "bandpass_range": [1.0, 45.0] if apply_bandpass else None,
                "sfreq_final": sfreq,
                "preprocessing_version": "1.0-hardened"
            }
        }
        
        # --- 2. SPECTRAL & INTERPRETATION CACHE (Level 3/4) ---
        cached_res = get_cached_spectral(file_path, start, duration, result["preprocessing"])
        if cached_res:
             # Merge cached data into current result (preserving window/preproc context)
             for key in ["quality", "qeeg", "temporal_qeeg", "topography", "normative", "normative_topography", "interpretation", "features", "baseline_comparison"]:
                 if key in cached_res:
                     result[key] = cached_res[key]
             return result

        # --- 3. MODULAR ANALYSIS MODULES ---
        if include_quality:
            result["quality"] = compute_segment_quality(data_uv, channels, sfreq, context=context)
            
            # Application of quality override (Validation/Benchmark support)
            if quality_override:
                for key, val in quality_override.items():
                    if isinstance(val, dict) and key in result["quality"] and isinstance(result["quality"][key], dict):
                        result["quality"][key].update(val)
                    else:
                        result["quality"][key] = val
            
            # --- 6. qEEG LAYER ---
            result["qeeg"] = compute_qeeg_layer(
                data_uv=data_uv,
                channels=channels,
                sfreq=sfreq,
                quality_info=result["quality"],
                confidence_info=result["quality"].get("confidence_details", {})
            )
            
            # --- 7. TEMPORAL DYNAMICS & SNAPSHOTS (Phase 3 Upgrade) ---
            history_qeeg = []
            history_snapshots = []
            step = 10.0
            t_back = start - step
            
            with profile_block("Temporal History Processing"):
                while t_back >= total_start and (start - t_back) <= 120.0:
                    rel_t = t_back - total_start
                    h_start_idx = int(rel_t * sfreq)
                    h_stop_idx = int((rel_t + step) * sfreq)
                    h_stop_idx = min(h_stop_idx, full_data_uv.shape[1])
                    h_data = full_data_uv[:, h_start_idx:h_stop_idx]
                    
                    h_qual = compute_segment_quality(h_data, channels, sfreq, context=context)
                    
                    if h_qual.get("eeg_quality_score", 0) >= 50 and h_qual.get("confidence_score", 0) >= 50:
                        h_qeeg = compute_qeeg_layer(
                            data_uv=h_data,
                            channels=channels,
                            sfreq=sfreq,
                            quality_info=h_qual,
                            confidence_info=h_qual.get("confidence_details", {})
                        )
                        
                        if h_qeeg["is_available"]:
                            history_qeeg.insert(0, h_qeeg)
                            
                            # Phase 3: Generate a shallow interpretation snapshot for history persistence
                            h_norm = compute_normative_comparison(
                                qeeg_results=h_qeeg, age=age, age_band=age_band, context=context
                            )
                            # We run a minimal interpretation (no history for history to avoid recursion)
                            from app.eeg.qeeg.interpretation.rules import extract_findings
                            from app.eeg.qeeg.interpretation.confidence import compute_interpretation_confidence
                            h_conf = compute_interpretation_confidence(h_qeeg, h_qual)
                            h_findings = extract_findings(h_qeeg, h_norm, h_conf)
                            
                            history_snapshots.insert(0, {
                                "findings": [finding_obj.model_dump() for finding_obj in h_findings],
                                "interpretation_eligible": True
                            })
                    
                    t_back -= step
                
            result["temporal_qeeg"] = compute_temporal_qeeg(
                history=history_qeeg,
                current_qeeg=result["qeeg"],
                window_step=step
            )

            # --- 8. SPATIAL TOPOGRAPHY ---
            result["topography"] = compute_band_topographies(
                channel_metrics=result["qeeg"].get("channel_metrics", []),
                qeeg_trust_level=result["qeeg"].get("trust_level", "unavailable")
            )

            # --- 9. NORMATIVE COMPARISON ---
            result["normative"] = compute_normative_comparison(
                qeeg_results=result["qeeg"],
                age=age,
                age_band=age_band,
                context=context
            )

            # --- 10. NORMATIVE TOPOGRAPHY ---
            result["normative_topography"] = compute_normative_topography(
                normative_layer=result["normative"],
                qeeg_trust_level=result["qeeg"].get("trust_level", "unavailable")
            )

            # --- 11. INTERPRETIVE INTELLIGENCE (Phase 3 Integration) ---
            # Synthesis layer: now accepts window history and comparison targets
            topography_ctx = {
                "topography": result.get("topography"),
                "window": result.get("window"),
                "preprocessing": result.get("preprocessing")
            }
            
            interp_result = run_interpretation(
                qeeg_results=result["qeeg"],
                normative_results=result["normative"],
                quality_results=result["quality"],
                topography_context=topography_ctx,
                historical_snapshots=history_snapshots,
                comparison_target=comparison_target
            )
            # Convert Pydantic model to dict for JSON serialization
            result["interpretation"] = interp_result.model_dump()
            
            # Standardization for Phase 20A UI
            result["interpretation_status"] = "ready"
            result["interpretation_skip_reason"] = None
            if result.get("quality", {}).get("is_rejected", False):
                result["interpretation_status"] = "skipped"
                result["interpretation_skip_reason"] = "Signal quality rejected by core engine"
            elif not result["interpretation"].get("summary", {}).get("primary_points"):
                result["interpretation_status"] = "unavailable"

            # --- 11.2 VISUALIZATION PLUGINS (Hook Stage C) ---
            with profile_block("Visualization Plugins"):
                viz_plugins = manager.run_visualization_plugins(result)
                result["plugin_results"].extend([p.model_dump() for p in viz_plugins])

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

            # --- 11.5 SECONDARY ML ADVISORY (Phase 15 Addition) ---
            with profile_block("ML Advisory Layer"):
                ml_result = run_ml_advisory(
                    data_uv=data_uv,
                    sfreq=sfreq,
                    channels=channels,
                    full_result_context=result,
                    research_mode=research_mode
                )
                result["advisory_ml"] = ml_result.model_dump()
                

                # Check for Visible Disagreement (Primary vs ML)
                # If ML detects EMG > 0.7 but Heuristics say Clean, flag it
                if research_mode:
                    emg_ml = next((p for p in ml_result.artifact_predictions if p.label == "emg_contamination"), None)
                    if emg_ml and emg_ml.probability > 0.7:
                        # Logic to add a behavior flag if primary rule engine missed it
                        if "artifact_detected" not in result["interpretation"]["behavior_flags"]:
                            result["interpretation"]["behavior_flags"].append("ml_disagreement_artifact_shadow")

        # Features: Computes absolute and relative band power using Welch's method.
        if include_features:
            features = extract_features(data_uv, sfreq, channels)
            result["features"] = features
            
            # --- 11.3 ANALYTICS PLUGINS (Hook Stage B) ---
            with profile_block("Analytics Plugins"):
                ana_plugins = manager.run_analytics_plugins(data_uv, sfreq, channels)
                result["plugin_results"].extend([p.model_dump() for p in ana_plugins])
            
            # Baseline Comparison: Direct comparison to a stored resting/calibration record.
            # This allows the UI to highlight deviations (e.g., '140% of baseline delta').
            if include_baseline:
                baseline_obj = load_baseline(db, user_id, baseline_type)
                if baseline_obj:
                    result["baseline_comparison"] = compare_to_baseline(features, baseline_obj.features)
                else:
                    result["baseline_comparison"] = {"error": "No baseline configured"}

        # --- 12. STORE CACHE ---
        set_cached_spectral(file_path, start, duration, result["preprocessing"], result)

        return result
        
    except Exception as e:
        # Surface internal errors gracefully with meaningful details
        raise HTTPException(status_code=500, detail=f"Error executing analysis pipeline: {str(e)}")
