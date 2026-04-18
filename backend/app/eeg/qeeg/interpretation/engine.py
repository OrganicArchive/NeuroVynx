"""
NeuroVynx: Interpretation Orchestrator
======================================
This module serves as the central synthesis layer for the diagnostic-agnostic 
interpretive engine. It coordinates the cross-validation of signal quality, 
quantitative metrics, and normative comparison to produce a coherent research insight.

Design Philosophy:
- Confidence-Gating: Interpretations are scaled by the underlying signal fidelity (SNR).
- Non-Diagnostic: Focuses on descriptive spatial and temporal band power variations.
- Deterministic: Uses a rule-based expert system for reliable and reproducible findings.
"""

from typing import Dict, Optional, List
from .models import InterpretationResult, InterpretationMetadata
from .confidence import compute_interpretation_confidence
from .rules import extract_findings
from .patterns import detect_patterns
from .summaries import generate_summary
from .temporal_gating import aggregate_temporal_support
from .interpretive_intelligence import run_interpretive_synthesis
from app.eeg.utils.performance_profiler import profile_function, profile_block

@profile_function("Interpretive Intelligence Layer")
def run_interpretation(
    qeeg_results: Dict,
    normative_results: Dict,
    quality_results: Dict,
    topography_context: Optional[Dict] = None,
    historical_snapshots: Optional[List[Dict]] = None,
    comparison_target: Optional[Dict] = None
) -> InterpretationResult:
    """
    Executes the full interpretive processing chain using a multi-stage synthesis model.
    Now includes Phase 3 Temporal Truthfulness and Longitudinal Trend Analysis.
    
    Args:
        qeeg_results: Quantitative metrics.
        normative_results: Z-score deviations.
        quality_results: Signal integrity scores.
        topography_context: Metadata regarding the spatial interpolation.
        historical_snapshots: List of prior window interpretation snapshots.
        comparison_target: (Explicit) previous session record for trend analysis.
    """
    
    # 1. Compute interpretive confidence
    confidence = compute_interpretation_confidence(
        qeeg_results=qeeg_results,
        quality_results=quality_results
    )
    
    # 2. Extract deterministic findings
    findings = extract_findings(
        qeeg_results=qeeg_results,
        normative_results=normative_results,
        confidence_result=confidence
    )
    
    # 3. Aggregate Temporal Support (Phase 3)
    # Moving from snapshots to evidence-backed persistence
    if historical_snapshots:
        # Determine if current window is interpretation eligible
        # (This logic mirrors normative_gating but at the interpretation layer)
        current_eligible = quality_results.get("confidence_score", 0) >= 50
        
        # findings is currently a List[FindingResult], we need to work with dicts for gating
        finding_dicts = [f.model_dump() for f in findings]
        
        enriched_finding_dicts = aggregate_temporal_support(
            current_findings=finding_dicts,
            historical_snapshots=historical_snapshots,
            current_eligible=current_eligible
        )
        
        # Re-parse into FindingResult models and refine wording
        from .models import FindingResult
        from .rules import refine_finding_wording
        findings = []
        for f_dict in enriched_finding_dicts:
            f_model = FindingResult(**f_dict)
            refine_finding_wording(f_model)
            findings.append(f_model)
    
    # 4. Detect higher-order patterns (as Candidates)
    patterns = detect_patterns(
        findings=findings,
        confidence_result=confidence,
        quality_results=quality_results
    )
    
    # 5. Final Synthesis Layer (Phase 4)
    # This replaces isolated wording logic with multi-layer evidence synthesis
    findings, patterns, metadata = run_interpretive_synthesis(
        candidate_findings=findings,
        candidate_patterns=patterns,
        normative_results=normative_results,
        quality_results=quality_results,
        confidence_result=confidence
    )
    
    # 5. Longitudinal Trend Analysis (Phase 3)
    trend_traceability = None
    if comparison_target:
        from .trend_analysis import run_trend_analysis
        
        # We need to construct a 'current' context that matches the expected dict structure 
        # for trend analysis (qeeg summary, window channels, etc.)
        current_payload = {
            "qeeg": qeeg_results,
            "window": topography_context.get("window", {}) if topography_context else {},
            "preprocessing": topography_context.get("preprocessing", {}) if topography_context else {}
        }
        
        with profile_block("Longitudinal Trend Analysis"):
            trend_traceability = run_trend_analysis(
                current_payload=current_payload,
                previous_payload=comparison_target
            )
            # Link to confidence model for summary reporting and validation
            confidence.trend_traceability = trend_traceability
    
    # 6. Generate natural-language summaries
    with profile_block("Natural Language Summary Generation"):
        summary = generate_summary(
            findings=findings,
            patterns=patterns,
            confidence=confidence
        )
    
    # 7. Assemble final payload
    top_p = [p.label for p in patterns if p.priority == "primary" and not p.suppression_info.is_suppressed]
    if not top_p:
        top_p = [find_obj.finding_name.replace("_", " ").title() for find_obj in findings if find_obj.priority == "primary" and not find_obj.suppression_info.is_suppressed][:2]

    return InterpretationResult(
        confidence=confidence,
        findings=findings,
        patterns=patterns,
        top_patterns=top_p,
        summary=summary,
        behavior_flags=summary.behavior_flags,
        trend_traceability=trend_traceability,
        metadata=metadata
    )
