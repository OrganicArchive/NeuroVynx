"""
NeuroVynx: Temporal Interpretation Engine
========================================
Classifies the stability and evolution of findings across a recording.
"""

from typing import List, Dict, Any
from .models import (
    WindowInterpretationSnapshot, 
    TemporalPatternResult, 
    FindingResult, 
    PatternResult
)

# Threshold Constants
THRESHOLD_PERSISTENT = 0.60
THRESHOLD_INTERMITTENT = 0.20
MIN_CONFIDENCE_STABLE = 0.40

def classify_temporal_stability(
    snapshots: List[WindowInterpretationSnapshot]
) -> List[TemporalPatternResult]:
    """
    Analyzes findings and patterns across windows to determine their temporal behavior.
    """
    temporal_results = []
    if not snapshots:
        return temporal_results

    # 1. Group Findings/Patterns by unique identifiers
    # We'll use (type, band, region/channel) as a key
    grouped_evidence: Dict[str, List[Dict[str, Any]]] = {}

    for i, s in enumerate(snapshots):
        # Process Findings
        for f in s.findings:
            key = f"{f.type}:{f.band or ''}:{f.region or ''}:{f.channel or ''}"
            if key not in grouped_evidence:
                grouped_evidence[key] = []
            grouped_evidence[key].append({
                "window_index": i,
                "confidence": f.confidence_score,
                "is_artifact_linked": s.confidence.global_score < 0.4 # Simplified link
            })

        # Process Patterns
        for p in s.patterns:
            key = f"pattern:{p.type}:{','.join(p.bands)}:{','.join(p.regions)}"
            if key not in grouped_evidence:
                grouped_evidence[key] = []
            grouped_evidence[key].append({
                "window_index": i,
                "confidence": p.confidence_score,
                "is_artifact_linked": p.suppressed_due_to_artifact
            })

    # 2. Compute Temporal Scores and Classify
    total_windows = len(snapshots)
    for key, observations in grouped_evidence.items():
        windows_present = len(set(o["window_index"] for o in observations))
        persistence_ratio = windows_present / total_windows
        mean_conf = sum(o["confidence"] for o in observations) / len(observations)
        artifact_overlap_count = sum(1 for o in observations if o["is_artifact_linked"])
        artifact_overlap_ratio = artifact_overlap_count / len(observations)

        # Classification Logic
        classification = "TRANSIENT"
        explanation = "Finding appeared sporadically with low overall recurrence."

        if artifact_overlap_ratio > 0.5:
            classification = "ARTIFACT-LINKED"
            explanation = "Findings heavily overlap with segments identified as containing high artifact burden."
        elif persistence_ratio >= THRESHOLD_PERSISTENT and mean_conf >= MIN_CONFIDENCE_STABLE:
            classification = "PERSISTENT"
            explanation = f"Findings were consistently observed across {persistence_ratio*100:.0f}% of sampled windows."
        elif persistence_ratio >= THRESHOLD_INTERMITTENT:
            classification = "INTERMITTENT"
            explanation = f"Findings appeared intermittently ({persistence_ratio*100:.0f}% presence) throughout the recording."
        
        # Check for Evolving (very simple slope check for this phase)
        # If confidence or severity is increasing/decreasing over time
        if windows_present >= 3:
            first_idx = observations[0]["window_index"]
            last_idx = observations[-1]["window_index"]
            if last_idx > first_idx + (total_windows // 2): # Spread across at least half the sampled recording
                # (Actual evolution logic would be more complex, but we'll flag it if there's clear spread)
                # classification = "EVOLVING" (requires more refined metrics)
                pass

        # Prepare label
        label = key.split(":")[-1] or key.split(":")[-2] or key.split(":")[-4]
        if "pattern:" in key:
            label = key.split(":")[1].replace("_", " ").title()
        else:
            # Format finding label: "elevated alpha in frontal"
            # Actually, let's just use a clean label
            parts = key.split(":")
            if parts[0] == "regional_band_power_abnormality":
                label = f"{parts[1].capitalize()} {parts[2]} deviation"
            else:
                label = parts[0].replace("_", " ").title()

        temporal_results.append(TemporalPatternResult(
            pattern_label=label,
            temporal_classification=classification,
            windows_present=windows_present,
            windows_total=total_windows,
            persistence_ratio=float(persistence_ratio),
            mean_confidence=float(mean_conf),
            confidence_level="high" if mean_conf > 0.7 else "moderate" if mean_conf > 0.4 else "low",
            artifact_overlap_ratio=float(artifact_overlap_ratio),
            explanation=explanation
        ))

    return temporal_results
