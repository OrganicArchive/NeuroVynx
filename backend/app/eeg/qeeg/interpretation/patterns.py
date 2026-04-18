"""
NeuroVynx: Pattern Detection & Synthesis Layer
==============================================
Groups findings into higher-order research patterns and applies artifact suppression.
"""

from typing import List, Dict, Set
from .models import FindingResult, PatternResult, ConfidenceResult
from app.eeg.config.analysis_standards import MIN_REGIONAL_SUPPORT_COUNT

def aggregate_pattern_temporal_state(findings: List[FindingResult]) -> str:
    """Identifies the dominant temporal state for a pattern based on its contributors."""
    if not findings:
        return "transient"
        
    states = [f.temporal_metadata.temporal_classification for f in findings if f.temporal_metadata]
    if not states:
        return "transient"
        
    # Standard hierarchy: stable > sustained > recurring > transient
    if "stable" in states: return "stable"
    if "sustained" in states: return "sustained"
    if "recurring" in states: return "recurring"
    return "transient"

def detect_patterns(
    findings: List[FindingResult],
    confidence_result: ConfidenceResult,
    quality_results: Dict
) -> List[PatternResult]:
    """
    Synthesizes higher-order patterns from a list of structured findings.
    
    Logic:
    - Clusters findings by band and region.
    - Suppresses findings that overlap heavily with artifact-contaminated zones.
    - Requires multiple findings for a 'robust' pattern.
    - Phase 3: Patterns inherit the temporal persistence of their supporting findings.
    """
    patterns = []
    
    # 1. Group Findings by Category for easier analysis
    by_band_direction = {}
    for f in findings:
        key = (f.band, f.direction)
        if key not in by_band_direction:
            by_band_direction[key] = []
        by_band_direction[key].append(f)
        
    # 2. Pattern: Frontal Theta Predominance
    # Criteria: Multiple frontal findings with elevated theta
    theta_elevated = by_band_direction.get(("theta", "elevated"), [])
    frontal_theta = [f for f in theta_elevated if f.region == "Frontal" or (f.channel and "F" in f.channel and "P" not in f.channel)]
    
    if len(frontal_theta) >= MIN_REGIONAL_SUPPORT_COUNT:
        suppressed = False
        reasons = []
        # Check for blink artifacts as suppressor
        if any("Blink" in r for r in confidence_result.reasons):
            suppressed = True
            reasons.append("Finding strongly overlaps with identified eye-blink artifacts in frontal sensors.")
            
        patterns.append(PatternResult(
            type="frontal_theta_predominance",
            label="Frontal Theta Predominance",
            regions=["Frontal"],
            bands=["theta"],
            supporting_findings=[f.finding_name for f in frontal_theta],
            confidence_score=float(confidence_result.per_region.get("Frontal", 0.5)),
            detected=True,
            eligible=True,
            priority="primary",
            suppressed_due_to_artifact=suppressed,
            explanation="A cluster of elevated theta power was detected in the frontal regions.",
            temporal_classification=aggregate_pattern_temporal_state(frontal_theta)
        ))

    # 3. Pattern: Posterior Alpha Reduction
    # Criteria: Elevated or reduced alpha in occipital/parietal
    alpha_reduced = by_band_direction.get(("alpha", "reduced"), [])
    posterior_alpha = [f for f in alpha_reduced if f.region in ["Occipital", "Parietal"]]
    
    if len(posterior_alpha) >= MIN_REGIONAL_SUPPORT_COUNT:
        patterns.append(PatternResult(
            type="posterior_alpha_reduction",
            label="Posterior Alpha Reduction",
            regions=["Occipital", "Parietal"],
            bands=["alpha"],
            supporting_findings=[f.finding_name for f in posterior_alpha],
            confidence_score=float(confidence_result.global_score),
            detected=True,
            eligible=True,
            priority="primary",
            explanation="Alpha power is reduced across posterior regions relative to the reference group.",
            temporal_classification=aggregate_pattern_temporal_state(posterior_alpha)
        ))

    # 4. Pattern: Focal vs Diffuse Slowing
    # Slow bands = delta, theta
    slow_findings = by_band_direction.get(("delta", "elevated"), []) + by_band_direction.get(("theta", "elevated"), [])
    unique_regions = {f.region for f in slow_findings if f.region}
    
    if len(unique_regions) > 2:
        patterns.append(PatternResult(
            type="diffuse_slowing",
            label="Diffuse Slowing Pattern",
            regions=list(unique_regions),
            bands=["delta", "theta"],
            supporting_findings=[f.finding_name for f in slow_findings[:5]],
            confidence_score=float(confidence_result.global_score),
            detected=True,
            eligible=True,
            priority="primary",
            explanation="Widespread elevation of slow-wave activity was observed across multiple cortical regions.",
            temporal_classification=aggregate_pattern_temporal_state(slow_findings)
        ))
    elif len(unique_regions) == 1:
        region = list(unique_regions)[0]
        focal_slow = [f for f in slow_findings if f.region == region]
        if len(focal_slow) >= MIN_REGIONAL_SUPPORT_COUNT:
            patterns.append(PatternResult(
                type="focal_slowing",
                label=f"Focal Slowing ({region})",
                regions=[region],
                bands=["delta", "theta"],
                supporting_findings=[f.finding_name for f in focal_slow],
                confidence_score=float(confidence_result.per_region.get(region, 0.5)),
                detected=True,
                eligible=True,
                priority="primary",
                explanation=f"Localized increase in slow-wave activity detected in the {region} region.",
                temporal_classification=aggregate_pattern_temporal_state(focal_slow)
            ))

    # 5. Likely Artifact-Driven Abnormality
    # If a region is very noisy and has an "abnormality", call it out.
    artifact_patterns = []
    for region, score in confidence_result.per_region.items():
        if score < 0.4: # Very low confidence region
            overlaps = [f for f in findings if f.region == region]
            if overlaps:
                patterns.append(PatternResult(
                    type="artifact_driven_abnormality",
                    label=f"Artifact-Driven Variation ({region})",
                    regions=[region],
                    bands=list({f.band for f in overlaps if f.band}),
                    supporting_findings=[f.finding_name for f in overlaps],
                    confidence_score=float(score),
                    detected=True,
                    eligible=True,
                    priority="technical_only",
                    suppressed_due_to_artifact=True,
                    explanation=f"Deviations in the {region} region overlap with significant signal artifacts."
                ))

    return patterns
