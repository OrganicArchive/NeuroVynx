"""
NeuroVynx: Normative Gating Module
==================================
Implements a three-tier eligibility system to ensure analytical truthfulness.

1. metric_available: The value was calculated.
2. metric_normative_eligible: Satisfies signal quality and context for comparison to norms.
3. metric_interpretation_eligible: Satisfies regional support and confidence for clinical reasoning.
"""

from typing import Dict, List, Optional, Tuple
from app.eeg.config.analysis_standards import (
    MIN_QUALITY_FOR_NORM, 
    MIN_INTERPRETATION_CONFIDENCE,
    MIN_REGIONAL_SUPPORT_COUNT,
    Z_SIGNIFICANCE_MILD
)

def assess_channel_eligibility(
    channel_name: str, 
    quality_score: float, 
    has_reference: bool
) -> Dict[str, bool]:
    """
    Tier 1 & 2: Determines if a channel can be compared to norms.
    """
    is_available = True # If we reach here, PSD was calculated
    is_eligible = has_reference and quality_score >= MIN_QUALITY_FOR_NORM
    
    # Interpretation eligibility at channel level requires high quality
    is_interpretable = is_eligible and quality_score >= 70 

    # [TRACE] Channel Gating Analysis
    if not is_interpretable:
        print(f"[TRACE:GATE] Channel {channel_name} disqualified. Quality: {quality_score:.1f}% (Required: 70%). HasRef: {has_reference}")

    return {
        "metric_available": is_available,
        "metric_normative_eligible": is_eligible,
        "metric_interpretation_eligible": is_interpretable,
        "ineligible_reason": None if is_eligible else "Low signal quality or missing reference"
    }

def assess_regional_eligibility(
    region_name: str,
    z_score: Optional[float],
    trusted_channel_count: int,
    mean_quality: float,
    interpretation_confidence: float
) -> Dict[str, bool]:
    """
    Tier 3: Determines if a regional finding is strong enough for interpretation.
    """
    is_available = z_score is not None
    
    # Normative eligible if we had any clean channels to average
    is_eligible = is_available and trusted_channel_count > 0 and mean_quality >= MIN_QUALITY_FOR_NORM
    
    # Interpretation eligible requires:
    # 1. Minimum support count (at least 2 electrodes)
    # 2. Minimum quality threshold
    # 3. Minimum overall interpretation confidence
    is_interpretable = (
        is_eligible and 
        trusted_channel_count >= MIN_REGIONAL_SUPPORT_COUNT and
        mean_quality >= 70 and
        interpretation_confidence >= MIN_INTERPRETATION_CONFIDENCE
    )
    
    reason = None
    if not is_eligible:
        reason = "Insufficient regional signal quality"
    elif not is_interpretable:
        if trusted_channel_count < MIN_REGIONAL_SUPPORT_COUNT:
            reason = f"Insufficient electrode support (n={trusted_channel_count})"
        else:
            reason = "Low interpretive confidence"

    # [TRACE] Regional Gating Analysis
    if not is_interpretable and is_available:
        print(f"[TRACE:GATE] Region {region_name} disqualified. Channels: {trusted_channel_count}, MeanQual: {mean_quality:.1f}%, Confidence: {interpretation_confidence:.1f}%")

    return {
        "metric_available": is_available,
        "metric_normative_eligible": is_eligible,
        "metric_interpretation_eligible": is_interpretable,
        "ineligible_reason": reason
    }
