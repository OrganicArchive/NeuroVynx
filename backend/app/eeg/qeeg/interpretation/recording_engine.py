"""
NeuroVynx: Recording-Level Orchestration Engine
===============================================
Handles the synthesis of whole-recording insights by sampling representative 
windows and applying temporal intelligence logic.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from app.eeg.analysis.pipeline import analyze_window
from app.models.session import Session
from .models import (
    RecordingInterpretationResult, 
    WindowInterpretationSnapshot,
    TemporalSummary,
    ConfidenceResult
)
from .advanced_patterns import synthesize_advanced_patterns
from .temporal import classify_temporal_stability

DEFAULT_SAMPLE_WINDOWS = 8
MIN_SAMPLE_WINDOWS = 3

def run_recording_interpretation(
    db: DBSession,
    session_id: str,
    sampling_config: Optional[Dict[str, Any]] = None
) -> RecordingInterpretationResult:
    """
    Orchestrates the full recording analysis workflow.
    
    Stages:
    1. Select representative windows across the recording.
    2. Execute window-level analysis for each selection.
    3. Synthesize advanced recording-level patterns.
    4. Classify temporal dynamics (persistence, intermittent, etc.).
    5. Generate narrative recording-level summary.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    duration = session.duration_seconds or 0.0
    num_samples = (sampling_config or {}).get("num_windows", DEFAULT_SAMPLE_WINDOWS)
    
    # 1. Select Representative Windows (Evenly Spaced)
    # --------------------------------------------------------------------------
    candidate_starts = _select_representative_windows(duration, num_samples)
    
    window_snapshots: List[WindowInterpretationSnapshot] = []
    skipped_windows: List[Dict[str, Any]] = []
    sampled_indices: List[int] = []

    # 2. Iterative Analysis
    # --------------------------------------------------------------------------
    for i, start_t in enumerate(candidate_starts):
        try:
            # Run existing window-level interpretation
            # We use 10s windows as standard
            window_res = analyze_window(
                db=db,
                session_id=session_id,
                start=start_t,
                duration=10.0,
                include_quality=True,
                include_features=True,
                include_baseline=True
            )
            
            interp = window_res.get("interpretation")
            if not interp:
                skipped_windows.append({"index": i, "start": start_t, "reason": "No interpretation result returned"})
                continue

            # Check if window was usable (Phase 5.1 relaxed gait)
            conf_score = interp["confidence"]["global_score"]
            if conf_score < 0.15: # Relaxed from 0.2
                skipped_windows.append({"index": i, "start": start_t, "reason": f"Low confidence ({conf_score:.2f})"})
                continue

            # Build Snapshot
            snapshot = WindowInterpretationSnapshot(
                window_index=i,
                start_time=start_t,
                end_time=start_t + 10.0,
                findings=interp["findings"],
                patterns=interp["patterns"],
                confidence=interp["confidence"],
                artifact_flags=window_res.get("quality", {}).get("warnings", [])
            )
            window_snapshots.append(snapshot)
            sampled_indices.append(i)

        except Exception as e:
            skipped_windows.append({"index": i, "start": start_t, "reason": f"Analysis error: {str(e)}"})
            continue

    # 3. Validation & Caveats
    # --------------------------------------------------------------------------
    caveats = []
    if len(window_snapshots) < num_samples:
        caveats.append(f"Only {len(window_snapshots)}/{num_samples} interpretable windows were available; recording confidence reduced.")
    
    if len(window_snapshots) < MIN_SAMPLE_WINDOWS:
        caveats.append("Insufficient usable data for robust temporal classification.")

    # 4. Advanced Pattern Synthesis
    # --------------------------------------------------------------------------
    advanced_patterns = synthesize_advanced_patterns(window_snapshots)

    # 5. Temporal Classification
    # --------------------------------------------------------------------------
    temporal_patterns = classify_temporal_stability(window_snapshots)

    # 6. Generate Recording-Level Summary
    # --------------------------------------------------------------------------
    summary = _generate_recording_summary(temporal_patterns, caveats)

    # 7. Compute Overall Confidence
    # --------------------------------------------------------------------------
    if window_snapshots:
        overall_conf = sum(s.confidence.global_score for s in window_snapshots) / len(window_snapshots)
        # Reduce confidence if we have too many skipped windows
        sampling_penalty = (len(window_snapshots) / num_samples)
        overall_conf *= sampling_penalty
    else:
        overall_conf = 0.0

    return RecordingInterpretationResult(
        sampled_windows=sampled_indices,
        skipped_windows=skipped_windows,
        window_snapshots=window_snapshots,
        advanced_patterns=advanced_patterns,
        temporal_patterns=temporal_patterns,
        temporal_summary=summary,
        overall_confidence=float(overall_conf),
        overall_confidence_level="high" if overall_conf > 0.7 else "moderate" if overall_conf > 0.4 else "low",
        caveats=caveats
    )

def _select_representative_windows(recording_duration: float, num_windows: int) -> List[float]:
    """Generates evenly spaced candidate start times across the recording."""
    if recording_duration <= 10.0:
        return [0.0]
    
    # We want to avoid the very end where a window might be cut off
    effective_duration = max(0, recording_duration - 10.0)
    
    if num_windows <= 1:
        return [effective_duration / 2.0]
        
    return [float(i * (effective_duration / (num_windows - 1))) for i in range(num_windows)]

def _generate_recording_summary(temporal_patterns: List[Any], caveats: List[str]) -> TemporalSummary:
    """Produces the trust-aware narrative summary of the recording."""
    persistent = [p for p in temporal_patterns if p.temporal_classification == "PERSISTENT"]
    intermittent = [p for p in temporal_patterns if p.temporal_classification == "INTERMITTENT"]
    
    bullets = []
    
    if persistent:
        short = f"{persistent[0].pattern_label} was persistently observed across the recording."
        for p in persistent:
            bullets.append(f"Persistent finding: {p.pattern_label} ({p.persistence_ratio*100:.0f}% presence).")
    elif intermittent:
        short = f"{intermittent[0].pattern_label} appeared intermittently during the session."
    else:
        # Graceful fallback for low-evidence recordings
        if caveats:
            short = "Interpretation available with reduced certainty due to data quality."
        else:
            short = "No robust persistent patterns were identified across the sampled recording."

    detailed = short
    if persistent or intermittent:
        detailed += " Findings were distributed with varying stability across temporal segments."
    
    if caveats:
        detailed += f" Note: {caveats[0]}"
        for c in caveats:
            bullets.append(f"CAVEAT: {c}")

    return TemporalSummary(
        short=short,
        detailed=detailed,
        bullets=bullets
    )
