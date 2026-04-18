"""
NeuroVynx: Phase 9 Verification Script
=======================================
Validates the Interpretation Layer logic using mocked qEEG/Normative/Quality data.
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend", "app"))

try:
    from eeg.qeeg.interpretation.engine import run_interpretation
    from eeg.qeeg.interpretation.models import InterpretationResult
    print("SUCCESS: Modules imported correctly.\n")
except ImportError as e:
    print(f"FAILED: Import error: {e}")
    sys.exit(1)

def test_clean_abnormality():
    print("--- Scenario 1: Clean Abnormality (Frontal Theta) ---")
    qeeg = {
        "eligible_eeg_channels": 19,
        "excluded_eeg_channels": [],
        "regional_metrics": [{"region": "Frontal", "channel_count": 5}]
    }
    normative = {
        "is_available": True,
        "results": {
            "regional": {
                "Frontal": {
                    "theta": {"z_score": 2.5, "classification": "moderate deviation elevated"}
                }
            },
            "channels": {
                "F3": {"theta": {"z_score": 2.6, "classification": "moderate"}},
                "F4": {"theta": {"z_score": 2.4, "classification": "moderate"}}
            }
        }
    }
    quality = {
        "confidence_score": 90,
        "confidence_level": "very high",
        "per_channel_status": {"F3": {"status": "good"}, "F4": {"status": "good"}},
        "warnings": []
    }
    
    res = run_interpretation(qeeg, normative, quality)
    print(f"Confidence: {res.confidence.global_level} ({res.confidence.global_score})")
    print(f"Findings: {len(res.findings)}")
    print(f"Patterns: {[p.label for p in res.patterns]}")
    print(f"Summary (Short): {res.summary.short}")
    
    assert res.confidence.global_level == "high"
    assert any(p.type == "frontal_theta_predominance" for p in res.patterns)
    print("SUCCESS: Scenario 1 passed.\n")

def test_noisy_suppression():
    print("--- Scenario 2: Frontal Theta with Blink Artifacts ---")
    qeeg = {
        "eligible_eeg_channels": 17,
        "excluded_eeg_channels": ["F7", "F8"],
        "regional_metrics": [{"region": "Frontal", "channel_count": 3}]
    }
    normative = {
        "is_available": True,
        "results": {
            "regional": {
                "Frontal": {
                    "theta": {"z_score": 3.2, "classification": "marked deviation elevated"}
                }
            }
        }
    }
    quality = {
        "confidence_score": 65, # Moderate
        "confidence_level": "moderate",
        "per_channel_status": {"FP1": {"status": "warning"}},
        "warnings": ["Frontal Blink / Transient Detected"]
    }
    
    res = run_interpretation(qeeg, normative, quality)
    print(f"Confidence: {res.confidence.global_level} ({res.confidence.global_score})")
    pattern = next((p for p in res.patterns if p.type == "frontal_theta_predominance"), None)
    
    if pattern:
        print(f"Pattern Suppressed: {pattern.suppressed_due_to_artifact}")
        print(f"Suppression Reasons: {pattern.suppression_reasons}")
    
    print(f"Summary (Short): {res.summary.short}")
    
    assert res.confidence.global_level == "low" # Dropped due to blink + missing channels
    assert pattern is None or pattern.suppressed_due_to_artifact is True
    print("SUCCESS: Scenario 2 passed.\n")

if __name__ == "__main__":
    try:
        test_clean_abnormality()
        test_noisy_suppression()
        print("\nALL INTERPRETATION TESTS PASSED.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
