import sys
import os
import json
import numpy as np

# Mocking the app environment
from backend.app.eeg.qeeg.normative import build_normative_topomap_payload
from backend.app.eeg.qeeg.topography import compute_normative_topography

def test_normative_topography_logic():
    print("--- Testing Phase 3B: Normative Topography Logic ---")
    
    # 1. Mock Channel Z-Results
    # 8 channels supported
    mock_z_results = {
        "F3": {"alpha": {"z_score": 2.5}},
        "F4": {"alpha": {"z_score": 1.1}},
        "C3": {"alpha": {"z_score": 0.0}},
        "C4": {"alpha": {"z_score": -0.5}},
        "P3": {"alpha": {"z_score": -1.8}},
        "P4": {"alpha": {"z_score": -2.2}},
        "O1": {"alpha": {"z_score": 3.1}},
        "O2": {"alpha": {"z_score": 0.2}}
    }
    
    # 2. Test Payload Builder
    payload = build_normative_topomap_payload(mock_z_results, "trusted")
    
    assert payload["is_available"] == True
    assert payload["status"] == "available"
    assert "alpha" in payload["bands"]
    
    alpha_payload = payload["bands"]["alpha"]
    # max(|3.1|, |-2.2|, 2.0) = 3.1
    print(f"Symmetric Limit: {alpha_payload['symmetric_limit']}")
    assert alpha_payload["symmetric_limit"] == 3.1
    assert alpha_payload["z_max"] == 3.1
    assert alpha_payload["z_min"] == -2.2
    
    # 3. Test Topography Engine
    # Build a minimal qeeg_results mock for gating
    mock_qeeg_normative = {
        "is_available": True,
        "normative_allowed": True,
        "topomap_layer": payload
    }
    
    topo_result = compute_normative_topography(mock_qeeg_normative, "trusted")
    
    assert topo_result["is_available"] == True
    assert topo_result["map_type"] == "normative_z_map"
    assert "alpha" in topo_result["bands"]
    
    surface = np.array(topo_result["bands"]["alpha"]["surface"])
    print(f"Surface Shape: {surface.shape}")
    print(f"Surface Max Z: {np.max(surface)}")
    print(f"Surface Min Z: {np.min(surface)}")
    
    # Ensure zero is not wiped out (except by mask)
    # The mask area should have values, non-mask should be 0.
    mask_vals = surface[surface != 0]
    has_pos = np.any(mask_vals > 0)
    has_neg = np.any(mask_vals < 0)
    print(f"Has Positive Z in surface: {has_pos}")
    print(f"Has Negative Z in surface: {has_neg}")
    
    assert has_pos == True
    assert has_neg == True
    
    # 4. Test Gating (Low Trust)
    low_trust_payload = build_normative_topomap_payload(mock_z_results, "borderline")
    assert low_trust_payload["is_available"] == False
    assert low_trust_payload["status"] == "unavailable_low_trust"
    
    # 5. Test Gating (Insufficient Channels)
    few_channels = {"F3": {"alpha": {"z_score": 1.0}}}
    insufficient_payload = build_normative_topomap_payload(few_channels, "trusted")
    assert insufficient_payload["is_available"] == False
    assert insufficient_payload["status"] == "unavailable_insufficient_channel_support"

    print("\n--- ALL TESTS PASSED (Phase 3B Backend) ---")

if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.getcwd())
    test_normative_topography_logic()
