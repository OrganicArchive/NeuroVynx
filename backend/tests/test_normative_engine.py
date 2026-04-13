
import sys
import os

# Add backend to path
sys.path.append('backend')

from app.eeg.qeeg.normative import compute_normative_comparison

def test_normative_scenarios():
    print("--- Testing Normative Engine Gating ---")
    
    # Mock qEEG results
    qeeg_results = {
        "trust_level": "trusted",
        "regional_metrics": [
            {
                "region": "Occipital",
                "relative_power": {
                    "delta": 0.15,
                    "theta": 0.15,
                    "alpha": 0.95, # Very high Alpha compared to mean 0.55
                    "beta": 0.15
                }
            }
        ],
        "channel_metrics": [
            {
                "channel": "O1",
                "relative_power": {
                    "delta": 0.15,
                    "theta": 0.15,
                    "alpha": 0.95,
                    "beta": 0.15
                }
            }
        ]
    }

    # Scenario 1: No Age
    print("\nScenario 1: No Age provided")
    res1 = compute_normative_comparison(qeeg_results)
    print(f"Status: {res1['normative_status']} | Reason: {res1.get('reason')}")
    assert res1['normative_status'] == "unavailable_missing_age_group"

    # Scenario 2: Low Trust
    print("\nScenario 2: Low Trust (Borderline)")
    bad_qeeg = qeeg_results.copy()
    bad_qeeg["trust_level"] = "borderline"
    res2 = compute_normative_comparison(bad_qeeg, age=25)
    print(f"Status: {res2['normative_status']} | Reason: {res2.get('reason')}")
    assert res2['normative_status'] == "unavailable_low_trust"

    # Scenario 3: Valid Age 25
    print("\nScenario 3: Valid Age 25 (adult_18_40)")
    res3 = compute_normative_comparison(qeeg_results, age=25)
    print(f"Status: {res3['normative_status']}")
    print(f"Pattern Hint: {res3['summary']['pattern_hint']}")
    
    # Check Z-score for Occipital Alpha
    # Mean=0.55, Std=0.08, Obs=0.95 -> Z = (0.95 - 0.55) / 0.08 = 0.40 / 0.08 = 5.0
    occ_alpha = res3['results']['regional']['Occipital']['alpha']
    print(f"Occipital Alpha Z: {occ_alpha['z_score']}")
    print(f"Classification: {occ_alpha['classification']}")
    
    assert occ_alpha['z_score'] == 5.0
    assert "marked_deviation_elevated" in occ_alpha['classification']

    print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    test_normative_scenarios()
