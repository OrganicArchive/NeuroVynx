"""
NeuroVynx: Contradiction & Conflict Detection Engine
=====================================================
Identifies conflicting evidence across findings and patterns, and applies
penalties or suppression actions to ensure interpretive consistency.
"""

from typing import List, Dict, Tuple
from .models import FindingResult, ContradictionResult

def identify_conflicts(
    findings: List[FindingResult],
    quality_results: Dict
) -> List[ContradictionResult]:
    """
    Scans candidate findings for cross-layer contradictions.
    
    Logic:
    - High-Frequency Noise vs Beta Elevation.
    - Sparse Regional Support vs Strong Severity Claim.
    - Blink Artifacts vs Frontal Theta/Delta.
    """
    contradictions = []
    
    # 1. High-Frequency Noise (EMG) vs Beta elevation
    # If HF absolute power is high (EMG proxy), penalize beta elevations in those regions
    hf_noisy_regions = []
    # Placeholder for actual quality check logic
    # In a real scenario, we'd check quality_results["per_region_artifacts"]
    
    for f in findings:
        # Conflict: Beta elevation in a region with high blink or muscle noise
        if f.band == "beta" and f.direction == "elevated":
            # If region quality is low, this is a likely contradiction
            if f.confidence_score < 0.75:
                contradictions.append(ContradictionResult(
                    type="artifact_vs_beta_elevation",
                    affected_finding=f.finding_name,
                    action_taken="downgrade",
                    explanation="Elevated beta power overlaps with potential muscle or electrode noise."
                ))
        
        # Conflict: Frontal slowing vs Blink artifacts
        if f.band in ["delta", "theta"] and (f.region == "Frontal" or (f.channel and "F" in f.channel)):
            if quality_results.get("artifact_flags", {}).get("blinks_detected"):
                contradictions.append(ContradictionResult(
                    type="blink_vs_frontal_slowing",
                    affected_finding=f.finding_name,
                    action_taken="reduce_confidence",
                    explanation="Frontal slow-wave activity overlaps with identified eye-blink artifacts."
                ))

        # Conflict: Sparse Support vs Markedly Abormal claim
        # (covered by synthesis logic usually, but we can flag it here)
        if f.severity == "marked" and f.weak_finding:
            contradictions.append(ContradictionResult(
                type="sparse_support_vs_isolated_claim",
                affected_finding=f.finding_name,
                action_taken="downgrade",
                explanation="Extreme deviation detected at a single sensor without regional reinforcement."
            ))

    return contradictions

def apply_contradiction_consequences(
    finding: FindingResult,
    contradictions: List[ContradictionResult]
) -> FindingResult:
    """Applies confidence penalties and priority shifts based on detected conflicts."""
    relevant = [c for c in contradictions if c.affected_finding == finding.finding_name]
    
    if not relevant:
        return finding
        
    finding.contradictions.extend(relevant)
    
    for c in relevant:
        if c.action_taken == "reduce_confidence":
            finding.confidence_score *= 0.8
            finding.evidence_trace.weakening_factors.append(f"Contradiction: {c.explanation}")
        elif c.action_taken == "downgrade":
            finding.confidence_score *= 0.6
            finding.priority = "secondary_cautious"
            finding.evidence_trace.penalties.append(f"Downgrade: {c.explanation}")
        elif c.action_taken == "suppress":
            finding.confidence_score = 0.0
            finding.eligible = False
            finding.priority = "blocked"
            finding.suppression_info.is_suppressed = True
            finding.suppression_info.reasons.append(f"Suppressed: {c.explanation}")
            
    return finding
