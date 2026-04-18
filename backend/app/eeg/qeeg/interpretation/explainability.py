"""
NeuroVynx: Explainability & Reasoning Helpers
==============================================
Provides utilities for building evidence traces, selecting interpretation levels, 
and managing natural language hedging based on synthesized confidence.
"""

from typing import List, Dict, Optional
from .models import FindingEvidenceTrace

def select_language_level(confidence_score: float) -> str:
    """
    Maps synthesized confidence scores to specific wording tiers (Phase 5.2).
    
    Tiers:
    - > 0.88: strong_supported
    - 0.72 - 0.88: moderate_supported
    - 0.58 - 0.72: cautious
    - 0.45 - 0.58: brief
    - < 0.45: withheld (technical only)
    """
    if confidence_score >= 0.88:
        return "strong_supported"
    if confidence_score >= 0.72:
        return "moderate_supported"
    if confidence_score >= 0.58:
        return "cautious"
    if confidence_score >= 0.45:
        return "brief"
    return "withheld"

def build_evidence_trace(
    supporting: List[str],
    weakening: List[str] = None,
    penalties: List[str] = None,
    summary: Optional[str] = None
) -> FindingEvidenceTrace:
    """Constructs a structured evidence trace for a finding."""
    return FindingEvidenceTrace(
        supporting_evidence=supporting,
        weakening_factors=weakening or [],
        penalties=penalties or [],
        final_reasoning_summary=summary
    )

def get_temporal_wording_prefix(classification: str) -> str:
    """Returns the wording prefix for a given temporal classification."""
    mapping = {
        "transient": "A brief, isolated ",
        "recurring": "Intermittent ",
        "sustained": "A sustained ",
        "stable": "A stable and persistent "
    }
    return mapping.get(classification, "")

def get_temporal_wording_suffix(classification: str) -> str:
    """Returns the wording suffix for a given temporal classification."""
    mapping = {
        "transient": " was observed in a single segment",
        "recurring": " was observed across multiple segments",
        "sustained": " was observed throughout the recording",
        "stable": " was observed throughout the recording"
    }
    return mapping.get(classification, "")

def construct_final_summary_text(
    finding_name: str,
    band: str,
    direction: str,
    location: str,
    language_level: str,
    temporal_classification: Optional[str] = None
) -> str:
    """
    Synthesizes the final human-readable summary for a finding based on its 
    language level and temporal persistence.
    """
    prefix = ""
    suffix = ""
    
    if temporal_classification:
        prefix = get_temporal_wording_prefix(temporal_classification)
        suffix = get_temporal_wording_suffix(temporal_classification)
        
    # Language Level Hedging (Phase 5.2 Refinement)
    hedging = ""
    if language_level == "cautious":
        hedging = "preliminary evidence of possible "
    elif language_level == "brief":
        hedging = "isolated, minimal "
    elif language_level == "withheld":
        hedging = "technical-only trace of "
        
    subject = f"{band} power"
    
    # Clean up direction prefixing
    dir_text = f"elevated" if direction == "elevated" else "reduced"
    
    # Example: "A stable and persistent moderate elevation of theta power in the Frontal region..."
    return f"{prefix}{hedging}{dir_text} {subject} {location}{suffix}."
