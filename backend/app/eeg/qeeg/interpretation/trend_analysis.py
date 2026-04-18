"""
NeuroVynx: Longitudinal Trend Analysis Module
==============================================
Implements Phase 3 logic for comparing distinct recordings/summaries.

Core Logic:
- Global Comparability: Checks channel overlap and preprocessing standards.
- Magnitude Delta: Calculates weighted changes in key bands.
- Change Confidence: Scores the reliability of the observed change.
- Classifications: no reliable change, possible, probable, strong stable.
"""

from typing import Dict, Optional, List, Tuple
import numpy as np
from .models import TrendTraceability
from app.eeg.config.analysis_standards import (
    MIN_SESSION_OVERLAP_RATIO_FOR_TREND,
    STRONG_OVERLAP_THRESHOLD,
    MAX_ALLOWED_QUALITY_DELTA_SESSIONS,
    MIN_PREPROCESSING_COMPATIBILITY_SCORE,
    TREND_CONFIDENCE_MIN
)

def assess_trend_eligibility(
    current_context: Dict,
    previous_context: Dict
) -> Tuple[bool, bool, bool, float, str]:
    """
    Evaluates if two sessions can be compared reliably.
    
    Returns:
        (available, comparable, interpretable, overlap_ratio, reason)
    """
    # 1. Check Preprocessing Parity
    curr_prep = current_context.get("preprocessing", {})
    prev_prep = previous_context.get("preprocessing", {})
    
    # Simple version check for now
    prep_compatible = curr_prep.get("preprocessing_version") == prev_prep.get("preprocessing_version")
    
    # 2. Check Channel Overlap
    curr_channels = set(current_context.get("window", {}).get("channels", []))
    prev_channels = set(previous_context.get("window", {}).get("channels", []))
    
    if not curr_channels or not prev_channels:
        return True, False, False, 0.0, "Missing channel metadata in one or both sessions"
        
    common = curr_channels.intersection(prev_channels)
    total_unique = curr_channels.union(prev_channels)
    overlap_ratio = len(common) / len(total_unique)
    
    comparable = (overlap_ratio >= MIN_SESSION_OVERLAP_RATIO_FOR_TREND) and prep_compatible
    interpretable = comparable and overlap_ratio >= STRONG_OVERLAP_THRESHOLD
    
    reason = None
    if overlap_ratio < MIN_SESSION_OVERLAP_RATIO_FOR_TREND:
        reason = f"Insufficient channel overlap ({overlap_ratio*100:.0f}%)"
    elif not prep_compatible:
        reason = "Preprocessing standards mismatch"
        
    return comparable, comparable, interpretable, overlap_ratio, reason

def compute_longitudinal_change(
    current_summary: Dict,
    previous_summary: Dict,
    interpretable: bool,
    overlap_ratio: float
) -> Dict:
    """
    Computes magnitude and confidence of change for global bands.
    """
    bands = ["delta", "theta", "alpha", "beta"]
    curr_power = current_summary.get("global_relative_power", {})
    prev_power = previous_summary.get("global_relative_power", {})
    
    deltas = {}
    total_conf = 0.0
    
    for band in bands:
        curr_v = curr_power.get(band, 0.0)
        prev_v = prev_power.get(band, 0.0)
        
        abs_change = curr_v - prev_v
        pct_change = (abs_change / (prev_v + 1e-6)) * 100
        
        deltas[band] = {
            "abs": abs_change,
            "pct": pct_change
        }
    
    # Confidence Scoring
    # Base: Overlap quality
    conf_base = overlap_ratio
    # Penalty: If not fully interpretable
    conf_interpretable = 1.0 if interpretable else 0.6
    
    change_confidence = conf_base * conf_interpretable
    
    # Classification Logic (Conservative)
    classification = "no reliable change"
    max_pct_change = max([abs(d["pct"]) for d in deltas.values()])
    
    if change_confidence >= TREND_CONFIDENCE_MIN:
        if max_pct_change > 50:
            classification = "strong stable change"
        elif max_pct_change > 25:
            classification = "probable change"
        elif max_pct_change > 10:
            classification = "possible change"
            
    # Directional tag for the dominant band change
    dominant_band = current_summary.get("dominant_global_band", "alpha")
    dom_delta = deltas.get(dominant_band, {"abs": 0})["abs"]
    direction = "increase" if dom_delta > 0 else "reduction"
    
    if classification != "no reliable change":
        classification = f"{classification} ({direction} in {dominant_band})"

    return {
        "classification": classification,
        "confidence": float(change_confidence),
        "deltas": deltas
    }

def run_trend_analysis(
    current_payload: Dict,
    previous_payload: Dict
) -> TrendTraceability:
    """
    Orchestrates the Phase 3 longitudinal analysis between two session payloads.
    """
    # 1. Assess Eligibility
    available, comparable, interpretable, overlap, reason = assess_trend_eligibility(
        current_payload, previous_payload
    )
    
    if not comparable:
        return TrendTraceability(
            comparison_session_id=None, # Should be filled by caller
            comparable_channel_count=0,
            overlap_ratio=overlap,
            preprocessing_compatible=False,
            trend_available=available,
            trend_comparable=False,
            trend_interpretation_eligible=False,
            change_classification="ineligible for comparison",
            change_confidence_score=0.0,
            ineligibility_reason=reason
        )
        
    # 2. Compute Change
    curr_summary = current_payload.get("qeeg", {}).get("summary", {})
    prev_summary = previous_payload.get("qeeg", {}).get("summary", {})
    
    change_results = compute_longitudinal_change(
        curr_summary, prev_summary, interpretable, overlap
    )
    
    return TrendTraceability(
        comparison_session_id=None,
        comparable_channel_count=len(set(current_payload.get("window", {}).get("channels", [])).intersection(previous_payload.get("window", {}).get("channels", []))),
        overlap_ratio=overlap,
        preprocessing_compatible=True,
        trend_available=True,
        trend_comparable=True,
        trend_interpretation_eligible=interpretable,
        change_classification=change_results["classification"],
        change_confidence_score=change_results["confidence"],
        ineligibility_reason=None if interpretable else "Limited comparability metadata"
    )
