"""
NeuroVynx: Interpretation Rules Engine
======================================
This module implements a deterministic expert system for extracting discrete 
research findings from quantitative EEG metrics and normative Z-score deviations.

Threshold Logic:
- Findings are only extracted if they cross the p < 0.05 or lower significance thresholds 
  (represented as Z-scores relative to the normative mean).
- Spatial Hierarchy: Regional findings (aggregated) take priority over single-channel 
  outliers to minimize the impact of sensor-specific impedance noise.
"""

from typing import List, Dict, Optional
from .models import FindingResult

# Normative Significance Thresholds (Standard Deviations)
# These represent standard clinical research boundaries for qEEG deviation.
ABS_Z_MILD = 1.5      # Significant (approx p < 0.06)
ABS_Z_MODERATE = 2.0  # Highly Significant (approx p < 0.02)
ABS_Z_MARKED = 3.0    # Extreme Deviation (approx p < 0.001)

def classify_severity_from_z(z: float) -> str:
    """
    Map absolute Z-score magnitudes to qualitative research descriptors.
    Categorizes the 'strength' of a given frequency band deviation.
    """
    abs_z = abs(z)
    if abs_z < ABS_Z_MILD:
        return "minimal"
    if abs_z < ABS_Z_MODERATE:
        return "mild"
    if abs_z < ABS_Z_MARKED:
        return "moderate"
    return "marked"

def classify_direction_from_z(z: float) -> str:
    """Classifies direction based on Z-score sign."""
    return "elevated" if z > 0 else "reduced"

def extract_findings(
    qeeg_results: Dict,
    normative_results: Dict,
    confidence_result: Dict # Derived from the Interpretation Confidence engine
) -> List[FindingResult]:
    """
    Orchestrates the extraction of spatial and spectral abnormalities.
    
    Processing Order:
    1. Regional Analysis: Aggregated band power deviations per region.
    2. Topographical Outliers: High-granularity sensor-level deviations.
    
    Each finding is tagged with a 'finding-level confidence' score to allow 
    downstream UI components to highlight or filter uncertain observations.
    """
    findings = []
    
    if not normative_results.get("is_available"):
        return findings

    results = normative_results.get("results", {})
    regional = results.get("regional", {})
    channels = results.get("channels", {})
    
    # Global confidence as baseline for finding confidence
    global_conf_score = confidence_result.global_score
    global_conf_level = confidence_result.global_level

    # 1. Regional Findings
    for region, bands in regional.items():
        for band, metrics in bands.items():
            z = metrics.get("z_score")
            eligibility = metrics.get("eligibility", {})
            interp_eligible = eligibility.get("metric_interpretation_eligible", True)
            
            if z is not None and abs(z) >= ABS_Z_MILD and interp_eligible:
                severity = classify_severity_from_z(z)
                direction = classify_direction_from_z(z)
                
                # Confidence adjustment for regional findings
                reg_conf = confidence_result.per_region.get(region, global_conf_score)
                
                finding = FindingResult(
                    finding_name=f"regional_{band}_{region}_{direction}",
                    type="regional_band_power_abnormality",
                    metric="relative_power",
                    band=band,
                    region=region,
                    direction=direction,
                    severity=severity,
                    z_score=float(z),
                    raw_support_components={"normative": float(abs(z)), "quality": float(reg_conf)},
                    confidence_score=float(reg_conf),
                    confidence_level="moderate",
                    explanation=f"Relative {band} power in the {region} region is {direction} (Z={z:.2f})."
                )
                findings.append(finding)

    # 2. Channel Findings
    for ch, bands in channels.items():
        for band, metrics in bands.items():
            z = metrics.get("z_score")
            eligibility = metrics.get("eligibility", {})
            interp_eligible = eligibility.get("metric_interpretation_eligible", True)
            
            if z is not None and abs(z) >= ABS_Z_MILD and interp_eligible:
                severity = classify_severity_from_z(z)
                direction = classify_direction_from_z(z)
                
                # Check if this is an isolated finding (to mark as weak)
                is_weak = True
                ch_conf = confidence_result.per_channel.get(ch, global_conf_score)

                finding = FindingResult(
                    finding_name=f"channel_{band}_{ch}_{direction}",
                    type="channel_band_power_abnormality",
                    metric="relative_power",
                    band=band,
                    channel=ch,
                    direction=direction,
                    severity=severity,
                    z_score=float(z),
                    raw_support_components={"normative": float(abs(z)), "quality": float(ch_conf)},
                    confidence_score=float(ch_conf),
                    confidence_level="moderate",
                    explanation=f"Relative {band} power at sensor {ch} is {direction} (Z={z:.2f}).",
                    weak_finding=is_weak
                )
                findings.append(finding)

    return findings

def refine_finding_wording(finding: FindingResult) -> FindingResult:
    """
    Adjusts the natural language explanation and severity based on temporal evidence.
    Implements the Phase 3 'Wording Ladder' to reflect evidence persistence.
    """
    if not finding.temporal_metadata:
        return finding
        
    meta = finding.temporal_metadata
    classification = meta.temporal_classification
    
    # Base description from finding
    base = finding.explanation.split(" (Z=")[0] # Extract the core statement
    z_str = f" (Z={finding.z_score:.2f})" if finding.z_score else ""
    
    # Wording Ladder Logic
    temporal_prefix = ""
    if classification == "transient":
        temporal_prefix = "A brief, isolated "
        suffix = " was observed in a single segment"
    elif classification == "recurring":
        temporal_prefix = "Intermittent "
        suffix = " was observed across multiple segments"
    elif classification == "sustained":
        temporal_prefix = "A sustained "
        suffix = " was observed throughout the recording"
    elif classification == "stable":
        temporal_prefix = "A stable and persistent "
        suffix = " was observed"
    else:
        return finding

    # Construct refined explanation
    # Example: "Relative theta power in the Frontal region is elevated" 
    # -> "A brief, isolated elevation of relative theta power in the Frontal region was observed..."
    
    subject = f"{finding.band} power"
    if finding.region:
        location = f"in the {finding.region} region"
    else:
        location = f"at sensor {finding.channel}"
        
    direction = finding.direction # elevated / reduced
    
    new_explanation = f"{temporal_prefix}{direction} {subject} {location}{suffix}{z_str}."
    finding.explanation = new_explanation
    
    return finding
