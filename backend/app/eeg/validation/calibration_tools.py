"""
NeuroVynx: Threshold Calibration & Sensitivity Tools
=====================================================
Helps tune interpretive thresholds by evaluating suite-wide 
pass/fail impact of configuration changes.
"""

from typing import List, Dict, Any
from .validation_harness import ValidationHarness
from app.eeg.config import analysis_standards

def evaluate_threshold_sensitivity(
    threshold_name: str, 
    values: List[Any]
) -> Dict[Any, float]:
    """
    Runs the validation suite multiple times with varying threshold values
    and returns the overall pass rate for each.
    """
    results = {}
    original_value = getattr(analysis_standards, threshold_name, None)
    
    try:
        for val in values:
            setattr(analysis_standards, threshold_name, val)
            print(f"Calibrating {threshold_name} = {val}...")
            
            harness = ValidationHarness()
            suite_result = harness.run_full_suite()
            results[val] = suite_result.overall_pass_rate
            
    finally:
        # Restore original value
        if original_value is not None:
            setattr(analysis_standards, threshold_name, original_value)
            
    return results

def run_confidence_calibration_sweep():
    """Sweeps the minimum confidence threshold to find the optimal balance."""
    thresholds = [0.3, 0.4, 0.5, 0.6]
    perf = evaluate_threshold_sensitivity("CONFIDENCE_MIN_THRESHOLD", thresholds)
    
    print("\nConfidence Calibration Results:")
    print("-" * 30)
    for t, rate in perf.items():
        print(f"Threshold {t}: {rate*100:.1f}% Suite Pass Rate")
        
if __name__ == "__main__":
    # Example usage:
    run_confidence_calibration_sweep()
