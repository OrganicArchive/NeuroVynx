import json
import os

def create_benchmark_fixtures():
    fixtures_dir = os.path.join("backend", "tests", "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # 1. Frontal Theta Excess (Clean)
    # This case should trigger a "High Confidence" frontal theta pattern.
    frontal_theta_clean = {
        "metadata": {
            "name": "frontal_theta_clean",
            "description": "Clean signal with clear moderate theta elevation in frontal regions."
        },
        "inputs": {
            "qeeg": {
                "eligible_eeg_channels": 19,
                "excluded_eeg_channels": [],
                "regional_metrics": [{"region": "Frontal", "channel_count": 5}]
            },
            "normative": {
                "is_available": True,
                "results": {
                    "regional": {
                        "Frontal": {"theta": {"z_score": 2.5}}
                    }
                }
            },
            "quality": {
                "confidence_score": 95,
                "per_channel_status": {},
                "warnings": []
            }
        },
        "expected_outcomes": {
            "confidence_level": "high",
            "pattern_type": "frontal_theta_predominance",
            "suppressed": False
        }
    }
    
    # 2. Frontal Theta with Blink (Suppressed)
    # This case should trigger a "Suppressed" pattern due to blink overlap.
    frontal_theta_blink = {
        "metadata": {
            "name": "frontal_theta_blink",
            "description": "Frontal theta excess but with high blink burden warning."
        },
        "inputs": {
            "qeeg": {
                "eligible_eeg_channels": 17,
                "excluded_eeg_channels": ["Fp1", "Fp2"],
                "regional_metrics": [{"region": "Frontal", "channel_count": 3}]
            },
            "normative": {
                "is_available": True,
                "results": {
                    "regional": {
                        "Frontal": {"theta": {"z_score": 3.2}}
                    }
                }
            },
            "quality": {
                "confidence_score": 60,
                "per_channel_status": {},
                "warnings": ["Frontal Blink Detected"]
            }
        },
        "expected_outcomes": {
            "confidence_level": "low",
            "pattern_type": "frontal_theta_predominance",
            "suppressed": True
        }
    }

    with open(os.path.join(fixtures_dir, "benchmark_cases.json"), "w") as f:
        json.dump([frontal_theta_clean, frontal_theta_blink], f, indent=2)
    
    print(f"Fixtures created in {fixtures_dir}")

if __name__ == "__main__":
    create_benchmark_fixtures()
