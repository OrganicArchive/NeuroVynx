"""
NeuroVynx: Temporal Gating Module
==================================
This module implements the logic to establish temporal truthfulness by 
analyzing the persistence and stability of findings across multiple windows.

Core Logic:
- window_interpretation_eligible: Only valid windows are used for temporal claims.
- temporal_persistence_eligible: Requires MIN_WINDOWS_FOR_TEMPORAL_CLAIM.
- Classifications: transient, recurring, sustained, stable.
"""

from typing import List, Dict, Optional
import numpy as np
from app.eeg.config.analysis_standards import (
    MIN_WINDOWS_FOR_TEMPORAL_CLAIM,
    MIN_CONSECUTIVE_WINDOWS_FOR_SUSTAINED,
    PERSISTENCE_RATIO_SUSTAINED,
    PERSISTENCE_RATIO_RECURRING,
    MIN_VALID_WINDOWS_FOR_SUMMARY_CLAIM
)
from .models import FindingTemporalMetadata

def classify_temporal_state(
    present_indices: List[int],
    eligible_indices: List[int],
    total_eligible: int
) -> Dict:
    """
    Computes temporal metadata for a finding based on its occurrence pattern.
    
    Args:
        present_indices: Indices of windows where the finding was detected.
        eligible_indices: Indices of windows that were eligible for interpretation.
        total_eligible: Total count of eligible windows in the sequence.
    """
    if total_eligible == 0:
        return {
            "classification": "transient",
            "ratio": 0.0,
            "consecutive": 0,
            "visibility": "secondary",
            "confidence": 0.0
        }

    present_count = len(present_indices)
    ratio = present_count / total_eligible
    
    # Calculate max consecutive windows
    max_consecutive = 0
    if present_indices:
        current_consecutive = 1
        sorted_indices = sorted(present_indices)
        max_consecutive = 1
        for i in range(1, len(sorted_indices)):
            if sorted_indices[i] == sorted_indices[i-1] + 1:
                current_consecutive += 1
            else:
                max_consecutive = max(max_consecutive, current_consecutive)
                current_consecutive = 1
        max_consecutive = max(max_consecutive, current_consecutive)

    # Classification Logic
    classification = "transient"
    visibility = "secondary"
    
    # 1. Sustained: High ratio and consecutive support
    if ratio >= PERSISTENCE_RATIO_SUSTAINED and max_consecutive >= MIN_CONSECUTIVE_WINDOWS_FOR_SUSTAINED:
        classification = "sustained"
        visibility = "primary"
    # 2. Recurring: Moderate ratio or repeating pattern
    elif ratio >= PERSISTENCE_RATIO_RECURRING or present_count >= 2:
        classification = "recurring"
        visibility = "primary" if present_count >= MIN_WINDOWS_FOR_TEMPORAL_CLAIM else "secondary"
    # 3. Stable: If it covers almost all eligible windows
    if ratio >= 0.9 and total_eligible >= MIN_VALID_WINDOWS_FOR_SUMMARY_CLAIM:
        classification = "stable"
        visibility = "primary"

    # Temporal Confidence Calculation
    # Factors: Ratio, Coverage, and Consecutive support
    conf_ratio = ratio
    conf_coverage = min(1.0, total_eligible / 5.0) # Full confidence at 5+ windows
    conf_consecutive = min(1.0, max_consecutive / 3.0)
    
    temporal_confidence = (0.5 * conf_ratio) + (0.3 * conf_coverage) + (0.2 * conf_consecutive)

    return {
        "classification": classification,
        "ratio": ratio,
        "consecutive": max_consecutive,
        "visibility": visibility,
        "confidence": float(temporal_confidence)
    }

def aggregate_temporal_support(
    current_findings: List[Dict],
    historical_snapshots: List[Dict],
    current_eligible: bool
) -> List[Dict]:
    """
    Enriches current findings with temporal metadata derived from history.
    """
    # 1. Map findings to a key for tracking (type + band + region/channel)
    def get_finding_key(f):
        return f"{f.get('type')}_{f.get('band')}_{f.get('region') or f.get('channel')}"

    # 2. Identify eligible windows
    eligible_windows = []
    # History windows
    for snap in historical_snapshots:
        if snap.get("interpretation_eligible", True): # Assume eligible if not specified for now
            eligible_windows.append(snap)
            
    # Add current
    total_eligible_count = len(eligible_windows) + (1 if current_eligible else 0)
    eligible_indices = list(range(total_eligible_count))
    
    # 3. Track occurrences of each finding type
    finding_occurrences = {} # key -> list of indices
    
    # Populate from history
    for idx, snap in enumerate(historical_snapshots):
        for f in snap.get("findings", []):
            key = get_finding_key(f)
            if key not in finding_occurrences:
                finding_occurrences[key] = []
            finding_occurrences[key].append(idx)
            
    # Populate from current
    current_idx = len(historical_snapshots)
    for f in current_findings:
        key = get_finding_key(f)
        if key not in finding_occurrences:
            finding_occurrences[key] = []
        finding_occurrences[key].append(current_idx)

    # 4. Enforce temporal logic on current findings
    enriched_findings = []
    for f in current_findings:
        key = get_finding_key(f)
        present_indices = finding_occurrences.get(key, [])
        
        temporal_stats = classify_temporal_state(
            present_indices=present_indices,
            eligible_indices=eligible_indices,
            total_eligible=total_eligible_count
        )
        
        f["temporal_metadata"] = FindingTemporalMetadata(
            present_in_window_count=len(present_indices),
            eligible_window_count=total_eligible_count,
            persistence_ratio=temporal_stats["ratio"],
            consecutive_support_max=temporal_stats["consecutive"],
            temporal_classification=temporal_stats["classification"],
            temporal_confidence_score=temporal_stats["confidence"],
            summary_visibility=temporal_stats["visibility"]
        )
        enriched_findings.append(f)
        
    return enriched_findings
