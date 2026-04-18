from typing import List, Dict, Any, Tuple
from .models import FindingResult, PatternResult, ConfidenceResult, InterpretationSummary

def calculate_priority_score(item: Any) -> float:
    """Computes a weighted significance score for ranking findings and patterns."""
    confidence = getattr(item, "confidence_score", 0.0)
    
    # Breadth score
    if hasattr(item, "regions") and item.regions:
        breadth = min(1.0, len(item.regions) / 5.0)
    elif hasattr(item, "region") and item.region:
        breadth = 0.2
    else:
        breadth = 0.0
        
    # Temporal score
    temporal = 0.5
    if hasattr(item, "temporal_metadata") and item.temporal_metadata:
        temporal = item.temporal_metadata.persistence_ratio
        
    # Significance score (normative)
    significance = 0.5
    if hasattr(item, "z_score") and item.z_score is not None:
        significance = min(1.0, abs(item.z_score) / 4.0)
        
    return (confidence * 0.45) + (breadth * 0.20) + (temporal * 0.20) + (significance * 0.15)

def group_findings_by_type(findings: List[FindingResult]) -> List[Dict[str, Any]]:
    """Clusters regional findings into widespread or multi-regional groups."""
    groups: Dict[Tuple[str, str, str], List[FindingResult]] = {}
    
    for f in findings:
        key = (f.finding_name, f.band or "", f.direction)
        if key not in groups:
            groups[key] = []
        groups[key].append(f)
        
    clustered = []
    for key, members in groups.items():
        finding_name, band, direction = key
        regions = sorted(list(set(f.region for f in members if f.region)))
        
        # Determine breadth label
        if len(regions) >= 4:
            breadth_label = "Widespread"
        elif len(regions) >= 2:
            breadth_label = "Multi-regional"
        elif len(regions) == 1:
            breadth_label = f"Regional ({regions[0]})"
        else:
            breadth_label = "Focal"
            
        avg_conf = sum(f.confidence_score for f in members) / len(members)
        max_z = max([abs(f.z_score or 0.0) for f in members])
        
        # Professional phrase construction
        phrase = f"{breadth_label} {direction} in {band} activity"
        if len(regions) > 0 and len(regions) < 4:
            phrase += f" (predominantly {', '.join(regions)})"
        
        clustered.append({
            "label": phrase,
            "priority_score": calculate_priority_score(members[0]), # Simplified
            "confidence": avg_conf,
            "type": finding_name,
            "findings": members
        })
        
    return clustered

def generate_summary(
    findings: List[FindingResult],
    patterns: List[PatternResult],
    confidence: ConfidenceResult
) -> InterpretationSummary:
    """
    Constructs a professional, layered presentation report from synthesized findings and patterns.
    Optimizes for meaning density over finding counts.
    """
    
    # 1. SEGMENTATION & RANKING
    eligible_findings = [f for f in findings if not f.suppression_info.is_suppressed]
    eligible_patterns = [p for p in patterns if not p.suppression_info.is_suppressed]
    
    # Cluster findings
    grouped_findings = group_findings_by_type(eligible_findings)
    
    # Sort everything by calculated priority score
    ranked_patterns = sorted(eligible_patterns, key=calculate_priority_score, reverse=True)
    ranked_groups = sorted(grouped_findings, key=lambda x: x["priority_score"], reverse=True)
    
    # 2. POPULATE LAYERS
    primary_points = []
    secondary_points = []
    
    # Layer 1: Primary Conclusions
    # Patterns usually represent higher-order meaning
    for p in ranked_patterns:
        if p.confidence_score >= 0.7:
            primary_points.append(p.explanation)
            
    # Top grouped findings if they are strong
    for g in ranked_groups:
        if g["priority_score"] >= 0.6 and len(primary_points) < 5:
            # Avoid repeating patterns already in list
            if not any(g["type"] in p.supporting_findings for p in ranked_patterns if p.confidence_score >= 0.7):
                primary_points.append(f"{g['label']} was observed with {round(g['confidence']*100)}% confidence.")

    # Layer 2: Secondary Findings
    for g in ranked_groups:
        if 0.4 <= g["priority_score"] < 0.6:
            secondary_points.append(g["label"])
    
    # Handle empty states gracefully
    if not primary_points:
        primary_narrative = "No stable quantitative deviations were detected in this segment."
        if confidence.global_score < 0.6:
            primary_narrative = "Analysis completed, but evidence strength is limited."
    else:
        primary_narrative = f"Interpretative synthesis identified {len(primary_points)} well-supported pattern(s):"

    # Layer 3: Technical Metadata
    suppressed_count = sum(1 for f in findings if f.suppression_info.is_suppressed)
    technical_findings = [f for f in findings if f.priority == "technical_only"]
    
    technical_note = "Additional technical deviations were tracked but withheld from primary reporting due to limited collective support."
    
    # Confidence Banner
    banner = f"{confidence.global_level.capitalize()} Confidence Interpretation"
    
    # 3. CONSTRUCT SUMMARY & BEHAVIOR FLAGS
    behavior_flags = []
    
    ineligibility_suffix = ""
    if confidence.trend_traceability and not confidence.trend_traceability.trend_available:
        behavior_flags.append("trend_block_detected")
        ineligibility_suffix = " Analysis of longitudinal trends is currently blocked due to session mismatch or preprocessing incompatibility."

    if confidence.global_score < 0.4:
        behavior_flags.append("technical_only_visibility")

    if any(len(f.contradictions) > 0 for f in findings if not f.suppression_info.is_suppressed):
        behavior_flags.append("contradiction_detected")

    summary = InterpretationSummary(
        primary_narrative=(primary_narrative + ineligibility_suffix) if confidence.global_score >= 0.4 else "Interpretation is limited to technical-only visibility due to signal quality constraints.",
        primary_points=primary_points[:5],
        secondary_narrative="Secondary findings:" if secondary_points else None,
        secondary_points=secondary_points[:5],
        technical_note=technical_note,
        technical_items_count=len(technical_findings),
        suppressed_items_count=suppressed_count,
        confidence_banner=banner,
        summary_version="1.2-calibrated",
        behavior_flags=behavior_flags,
        # Backward compatibility
        short=primary_narrative,
        detailed=" ".join(primary_points + secondary_points),
        bullets=primary_points,
        technical_details={"confidence_synthesized": round(confidence.global_score, 2)}
    )
    
    return summary
