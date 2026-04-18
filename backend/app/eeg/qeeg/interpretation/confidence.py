"""
NeuroVynx: Interpretation Confidence Engine
===========================================
Calculates the statistical reliability of interpretive findings. 

This engine acts as a 'Gating Mechanism' for the interpretation layer. It evaluates 
the Signal-to-Noise Ratio (SNR) context and spatial coverage to determine if the 
current data slice supports a reliable research finding or if interpretation 
should be withheld due to artifact contamination.
"""

from typing import Dict, List, Optional
from .models import ConfidenceResult

# Wording thresholds
CONF_HIGH = 0.80
CONF_MODERATE = 0.55

def score_to_confidence_level(score: float) -> str:
    """
    Standardizes numerical confidence into research-grade categorical tiers.
    - High (>=0.8): Data is reliable for comparative analysis.
    - Moderate (>=0.55): Data contains artifacts; findings should be caveated.
    - Low (<0.55): Significant noise; interpretation likely unreliable.
    """
    if score >= CONF_HIGH:
        return "high"
    if score >= CONF_MODERATE:
        return "moderate"
    return "low"

def compute_interpretation_confidence(
    qeeg_results: Dict,
    quality_results: Dict,
) -> ConfidenceResult:
    """
    Performs a multi-dimensional confidence assessment.
    
    Interpretive confidence is distinct from raw signal quality:
    - Signal Quality: Is the binary data representative of brain activity?
    - Interpretive Confidence: Is the data consistent enough to compare to a norm?
    
    The final score represents the probability that the finding is physiological 
    rather than artifactual, using coverage and contamination as penalty vectors.
    """
    reasons = []
    
    # 1. Start with the baseline confidence from the quality engine
    # Convert from 0-100 to 0.0-1.0
    base_score = quality_results.get("confidence_score", 0) / 100.0
    
    # 2. Extract context from quality results
    per_channel = quality_results.get("per_channel_status", {})
    warnings = quality_results.get("warnings", [])
    recording_warnings = quality_results.get("recording_warnings", [])
    
    # 3. Penalize based on coverage
    eligible_count = qeeg_results.get("eligible_eeg_channels", 0)
    total_eeg = len(qeeg_results.get("excluded_eeg_channels", [])) + eligible_count
    
    coverage_penalty = 0.0
    if total_eeg > 0:
        missing_count = total_eeg - eligible_count
        if missing_count > 0:
            coverage_penalty = (missing_count / total_eeg) * 0.2
            reasons.append(f"{missing_count} channels excluded due to poor quality")
            
    # 4. Penalize based on specific artifact flags
    artifact_penalty = 0.0
    blink_detected = any("Blink" in w for w in warnings)
    emg_detected = any("EMG" in ch.upper() or "EMG" in str(per_channel.get(ch, {}).get("warnings", "")) for ch in per_channel)
    
    if blink_detected:
        artifact_penalty += 0.15
        reasons.append("High blink burden in frontal channels")
    
    # 5. Domain-specific confidence (Regional)
    per_region = {}
    regional_metrics = qeeg_results.get("regional_metrics", [])
    for reg_m in regional_metrics:
        region = reg_m["region"]
        count = reg_m["channel_count"]
        # Regional confidence is higher if more channels support it
        reg_conf = min(1.0, base_score * (0.8 + (count * 0.1)))
        per_region[region] = float(reg_conf)

    # 6. Per-Metric Confidence (Simplified)
    per_metric = {
        "relative_power": base_score,
        "asymmetry": base_score * 0.9 # Asymmetry is more noise-sensitive
    }

    # 7. Final Global Score
    global_score = max(0.0, base_score - coverage_penalty - artifact_penalty)
    
    # --- PHASE 5.2 CALIBRATION: Systematic Research Suppression ---
    if global_score < 0.70:
        # Cubic penalty ensures low-SNR data drops rapidly below research-readiness thresholds
        norm_score = (global_score / 0.70)
        global_score *= (norm_score ** 3) * 0.85 # Definitive 15% safety buffer for research grade

    # Safety: Penalize further if we have widespread warnings
    if len(warnings) > (total_eeg / 2) or len(recording_warnings) > 0:
        global_score *= 0.6 
        reasons.append("Widespread signal contamination observed")

    # Final label
    global_level = score_to_confidence_level(global_score)
    
    # Per-channel mapping (passthrough from quality status)
    per_channel_conf = {}
    for ch, status in per_channel.items():
        if status.get("status") == "good":
            per_channel_conf[ch] = 1.0
        elif status.get("status") == "warning":
            per_channel_conf[ch] = 0.6
        else:
            per_channel_conf[ch] = 0.0

    return ConfidenceResult(
        global_score=float(global_score),
        global_level=global_level,
        per_channel=per_channel_conf,
        per_region=per_region,
        per_metric=per_metric,
        reasons=reasons[:4] # Return top 4 unique reasons
    )
