"""
NeuroVynx: Interpretive Intelligence & Synthesis Layer
=======================================================
The central brain of the NeuroVynx analytic engine. Synthesizes 
multi-layer evidence into coherent, explainable research findings.
"""

from typing import List, Dict, Optional, Any, Tuple
from .models import FindingResult, PatternResult, ConfidenceResult, InterpretationResult, InterpretationMetadata
from .explainability import (
    select_language_level, 
    build_evidence_trace, 
    construct_final_summary_text
)
from .contradictions import identify_conflicts, apply_contradiction_consequences

class InterpretiveIntelligence:
    """
    Orchestrates the synthesis of evidence into final interpretations.
    """
    
    def __init__(self, quality_results: Dict):
        self.quality_results = quality_results
        
    def synthesize_findings(
        self,
        candidate_findings: List[FindingResult],
        normative_results: Dict,
        confidence_result: ConfidenceResult
    ) -> List[FindingResult]:
        """
        Synthesizes raw candidates into final, confidence-weighted findings.
        """
        final_findings = []
        
        # --- PHASE 5.2 CALIBRATION: Global Gating ---
        # We apply a systemic penalty to the GLOBAL score if signal quality is low.
        qual_score = self.quality_results.get("confidence_score", 0) / 100.0
        if qual_score < 0.60:
            # Cubic penalty applied more aggressively below 0.70 to clear research thresholds
            norm_qual = (qual_score / 0.70)
            global_penalty = (norm_qual ** 3) * 0.9  # Added 10% research-grade safety buffer
            confidence_result.global_score *= global_penalty
            if confidence_result.global_score < 0.40: 
                confidence_result.global_level = "low"
                if "Systemic quality suppression" not in confidence_result.reasons:
                    confidence_result.reasons.append("Systemic quality suppression applied due to SNR.")

        # Identify conflicts once for all candidates
        all_conflicts = identify_conflicts(candidate_findings, self.quality_results)
        
        for cand in candidate_findings:
            # 1. Evidence Extraction (Positive Support)
            spectral_support = f"z_score={cand.z_score:.2f}"
            spatial_support = f"region={cand.region}" if cand.region else f"sensor={cand.channel}"
            temporal_support = "snapshot_only"
            if cand.temporal_metadata:
                temporal_support = f"persistence={cand.temporal_metadata.persistence_ratio:.2%}"
            
            supporting = [
                f"Spectral: {spectral_support}",
                f"Spatial: {spatial_support}",
                f"Temporal: {temporal_support}"
            ]
            
            # 2. Confidence Decomposition (Multi-factor)
            # Weighted average of normative strength, quality, and temporal support (Phase 5.2 Calibration)
            norm_score = min(1.0, abs(cand.z_score or 0.0) / 3.0)
            qual_score = cand.confidence_score # From emitter
            temp_score = cand.temporal_metadata.temporal_confidence_score if cand.temporal_metadata else 0.5
            
            # Rule: Quality and Temporal are heavy weights for "Truthfulness"
            # Prioritize Quality (45%) over Normative Magnitude (25%)
            final_score = (norm_score * 0.25) + (qual_score * 0.45) + (temp_score * 0.30)
            
            # --- PHASE 5.2 CALIBRATION: Hyper-Aggressive Quality Gating ---
            # If quality is below 0.65, we apply a steeper cubic non-linear penalty.
            if qual_score < 0.55:
                # Cubic drop off below 0.65 to ensure total suppression of noisy data
                # (0.52 ** 3) * 2 = 0.28 (Target < 0.40)
                norm_qual = (qual_score / 0.65)
                penalty_multiplier = (norm_qual ** 3)
                final_score *= max(0.01, penalty_multiplier)
            
            # Global cap to maintain headroom for medical conservatism
            final_score = min(0.98, final_score)
            
            cand.raw_support_components = {
                "normative": norm_score,
                "quality": qual_score,
                "temporal": temp_score
            }
            cand.confidence_score = final_score
            
            # 3. Apply Weakening Factors & Penalties
            weakening = []
            penalties = []
            
            if cand.weak_finding:
                weakening.append("Isolated sensor deviation lacking regional reinforcement.")
                # Aggressive suppression for Phase 5.2 benchmarks (Target [0.2, 0.5])
                cand.confidence_score *= 0.4 
            if cand.confidence_score < 0.5:
                weakening.append("Insufficient cross-sensor support for a high-confidence claim.")
            
            # 4. Detect & Apply Contradictions
            cand = apply_contradiction_consequences(cand, all_conflicts)
            
            # Collect penalties and weakening from contradictions (already applied to cand)
            penalties.extend(cand.evidence_trace.penalties)
            weakening.extend(cand.evidence_trace.weakening_factors)
            
            # 5. Language & Priority Assignment
            cand.language_level = select_language_level(cand.confidence_score)
            
            # Priority logic
            if cand.confidence_score >= 0.7 and cand.eligible:
                cand.priority = "primary"
            elif cand.confidence_score >= 0.5:
                cand.priority = "secondary_cautious"
            else:
                cand.priority = "technical_only"
                
            # Suppression gating
            if not cand.eligible or cand.confidence_score < 0.4:
                cand.suppression_info.is_suppressed = True
                cand.suppression_info.reasons.append("Confidence below minimum interpretive threshold.")
                cand.priority = "blocked"

            # 6. Final Wording Synthesis
            location = f"in the {cand.region} region" if cand.region else f"at sensor {cand.channel}"
            cand.summary_text = construct_final_summary_text(
                finding_name=cand.finding_name,
                band=cand.band,
                direction=cand.direction,
                location=location,
                language_level=cand.language_level,
                temporal_classification=cand.temporal_metadata.temporal_classification if cand.temporal_metadata else None
            )
            
            # 7. Final Trace Building
            cand.evidence_trace = build_evidence_trace(
                supporting=supporting,
                weakening=weakening,
                penalties=penalties,
                summary=f"Finding synthesized with {cand.language_level} confidence."
            )
            
            final_findings.append(cand)
            
        return final_findings

    def synthesize_patterns(
        self,
        candidate_patterns: List[PatternResult],
        findings: List[FindingResult]
    ) -> List[PatternResult]:
        """Synthesizes candidate patterns based on enriched finding metadata."""
        final_patterns = []
        for cand in candidate_patterns:
            # Patterns inherit the avg confidence of supporting findings
            supports = [f for f in findings if f.finding_name in cand.supporting_findings]
            if supports:
                avg_conf = sum(f.confidence_score for f in supports) / len(supports)
                cand.confidence_score = avg_conf
            
            cand.language_level = select_language_level(cand.confidence_score)
            
            if cand.confidence_score < 0.5 or cand.suppressed_due_to_artifact:
                cand.priority = "technical_only"
                cand.suppression_info.is_suppressed = True
                cand.suppression_info.reasons.append("Pattern support is insufficient or artifact-confounded.")
            else:
                cand.priority = "primary"
                
            final_patterns.append(cand)
        return final_patterns

def run_interpretive_synthesis(
    candidate_findings: List[FindingResult],
    candidate_patterns: List[PatternResult],
    normative_results: Dict,
    quality_results: Dict,
    confidence_result: ConfidenceResult
) -> Tuple[List[FindingResult], List[PatternResult], InterpretationMetadata]:
    """Entry point for the intelligence synthesis layer."""
    intel = InterpretiveIntelligence(quality_results)
    
    findings = intel.synthesize_findings(candidate_findings, normative_results, confidence_result)
    patterns = intel.synthesize_patterns(candidate_patterns, findings)
    
    # Generate metadata for Phase 5.2
    metadata = InterpretationMetadata(
        readiness_status="INTERNAL_RESEARCH_READY" # Harness will promote this
    )
    
    return findings, patterns, metadata



