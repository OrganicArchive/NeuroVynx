"""
NeuroVynx: Advanced Pattern Library
===================================
Expands pattern recognition beyond atomic finding clusters into 
research-grade qEEG pattern families.
"""

from typing import List, Dict, Optional
from .models import (
    WindowInterpretationSnapshot, 
    AdvancedPatternResult, 
    FindingResult, 
    PatternResult
)

def synthesize_advanced_patterns(
    snapshots: List[WindowInterpretationSnapshot]
) -> List[AdvancedPatternResult]:
    """
    Synthesizes recording-level advanced patterns from a collection of window snapshots.
    
    Logic:
    - Identifies recurring spatial and spectral signatures.
    - Aggregates evidence across time to form robust pattern conclusions.
    - Implements hierarchy: Composite Patterns > Family Patterns > Atomic Patterns.
    """
    advanced_patterns = []
    
    if not snapshots:
        return advanced_patterns

    # 1. Gather all findings and patterns across all snapshots
    all_findings: List[FindingResult] = []
    for s in snapshots:
        all_findings.extend(s.findings)
        
    all_patterns: List[PatternResult] = []
    for s in snapshots:
        all_patterns.extend(s.patterns)

    # 2. Regional Slowing Analysis
    # --------------------------------------------------------------------------
    regional_slow_patterns = _detect_regional_slowing(snapshots)
    advanced_patterns.extend(regional_slow_patterns)

    # 3. Alpha Organization Analysis
    # --------------------------------------------------------------------------
    alpha_patterns = _detect_alpha_organization(snapshots)
    advanced_patterns.extend(alpha_patterns)

    # 4. Fast Activity Analysis
    # --------------------------------------------------------------------------
    fast_patterns = _detect_fast_activity_patterns(snapshots)
    advanced_patterns.extend(fast_patterns)

    # 5. Hemispheric Patterns
    # --------------------------------------------------------------------------
    hem_patterns = _detect_hemispheric_patterns(snapshots)
    advanced_patterns.extend(hem_patterns)

    # 6. Composite Pattern Synthesis
    # --------------------------------------------------------------------------
    composite_patterns = _synthesize_composite_patterns(advanced_patterns)
    advanced_patterns.extend(composite_patterns)

    return advanced_patterns

def _detect_regional_slowing(snapshots: List[WindowInterpretationSnapshot]) -> List[AdvancedPatternResult]:
    """Identifies stable clusters of elevated slow-wave activity (delta/theta)."""
    patterns = []
    regions = ["Frontal", "Central", "Posterior", "Temporal", "Occipital", "Parietal"]
    
    for region in regions:
        # Count windows where this region has elevated slow activity
        presence_count = 0
        confidences = []
        for s in snapshots:
            slow_findings = [f for f in s.findings if f.region == region and f.band in ["delta", "theta"] and f.direction == "elevated"]
            if len(slow_findings) >= 2: # At least 2 supporting findings in the window
                presence_count += 1
                confidences.append(s.confidence.per_region.get(region, s.confidence.global_score))
        
        # If present in at least 25% of sampled windows, call it a regional slowing pattern
        if presence_count >= max(1, len(snapshots) // 4):
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            label = f"{region} Slowing"
            family = "slowing"
            
            patterns.append(AdvancedPatternResult(
                type=f"{region.lower()}_slowing",
                label=label,
                family=family,
                bands=["delta", "theta"],
                regions=[region],
                supporting_findings=[f"Observed in {presence_count}/{len(snapshots)} sampled windows."],
                confidence_score=float(avg_conf),
                confidence_level="high" if avg_conf > 0.7 else "moderate" if avg_conf > 0.4 else "low",
                explanation=f"A recurring increase in {region} slow-wave activity was identified across the recording."
            ))

    return patterns

def _detect_alpha_organization(snapshots: List[WindowInterpretationSnapshot]) -> List[AdvancedPatternResult]:
    """Identifies patterns related to alpha rhythm stability and distribution."""
    patterns = []
    
    # 1. Posterior Alpha Reduction
    reduction_count = 0
    confidences = []
    for s in snapshots:
        alpha_red = [f for f in s.findings if f.band == "alpha" and f.direction == "reduced" and f.region in ["Occipital", "Parietal"]]
        if len(alpha_red) >= 1:
            reduction_count += 1
            confidences.append(s.confidence.global_score)
            
    if reduction_count >= max(1, len(snapshots) // 2):
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        patterns.append(AdvancedPatternResult(
            type="posterior_alpha_reduction",
            label="Posterior Alpha Reduction",
            family="alpha_organization",
            bands=["alpha"],
            regions=["Occipital", "Parietal"],
            supporting_findings=[f"Alpha reduction noted in {reduction_count}/{len(snapshots)} windows."],
            confidence_score=float(avg_conf),
            confidence_level="high" if avg_conf > 0.7 else "moderate",
            explanation="The posterior alpha rhythm is persistently reduced relative to the reference group."
        ))

    return patterns

def _detect_fast_activity_patterns(snapshots: List[WindowInterpretationSnapshot]) -> List[AdvancedPatternResult]:
    """Identifies clusters of elevated fast activity (beta)."""
    patterns = []
    
    # Diffuse Beta Elevation
    beta_count = 0
    for s in snapshots:
        beta_elev = [f for f in s.findings if f.band == "beta" and f.direction == "elevated"]
        if len({f.region for f in beta_elev if f.region}) >= 3:
            beta_count += 1
            
    if beta_count >= max(1, len(snapshots) // 2):
        patterns.append(AdvancedPatternResult(
            type="diffuse_beta_elevation",
            label="Diffuse Beta Elevation",
            family="fast_activity",
            bands=["beta"],
            regions=[],
            supporting_findings=[f"Widespread beta elevation in {beta_count}/{len(snapshots)} windows."],
            confidence_score=0.8,
            confidence_level="high",
            explanation="Diffuse elevation of beta-band activity was consistently observed."
        ))

    return patterns

def _detect_hemispheric_patterns(snapshots: List[WindowInterpretationSnapshot]) -> List[AdvancedPatternResult]:
    """Identifies left-right asymmetries."""
    patterns = []
    # Placeholder for hemispheric logic
    return patterns

def _synthesize_composite_patterns(patterns: List[AdvancedPatternResult]) -> List[AdvancedPatternResult]:
    """Combines individual advanced patterns into multi-system composites."""
    composites = []
    
    # Example: Diffuse Slowing + Alpha Reduction
    has_slowing = any("slowing" in p.type for p in patterns)
    has_alpha_red = any(p.type == "posterior_alpha_reduction" for p in patterns)
    
    if has_slowing and has_alpha_red:
        composites.append(AdvancedPatternResult(
            type="mixed_slow_and_alpha_reduction",
            label="Mixed Slow/Alpha Imbalance",
            family="composite",
            bands=["delta", "theta", "alpha"],
            regions=[],
            supporting_findings=["Co-occurrence of regional slowing and posterior alpha reduction."],
            confidence_score=min([p.confidence_score for p in patterns if p.family in ["slowing", "alpha_organization"]]),
            confidence_level="moderate",
            explanation="Recording exhibits a composite pattern of increased slow activity and decreased alpha organization.",
            composite_of=[p.type for p in patterns if p.family in ["slowing", "alpha_organization"]]
        ))
        
    return composites
