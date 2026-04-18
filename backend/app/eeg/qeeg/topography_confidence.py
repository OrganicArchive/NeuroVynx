"""
NeuroVynx: Topography Confidence Module
=======================================
Calculates numerical fidelity and spatial support for interpolated maps.
Determines the optimal rendering mode (Full, Cautious, Limited, Suppressed).
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from app.eeg.config.analysis_standards import (
    MIN_TOPO_CHANNELS,
    MIN_GEOMETRY_SCORE_FOR_FULL_RENDER,
    RENDER_MODES
)

def calculate_topo_fidelity(
    eligible_sensors: List[Dict[str, Any]], 
    distinct_regions: int,
    total_requested: int
) -> Dict[str, Any]:
    """
    Computes spatial support metrics and selects the UI render mode.
    """
    n_sensors = len(eligible_sensors)
    
    # 1. Base Coverage Score (Count vs Minimum)
    if n_sensors < MIN_TOPO_CHANNELS:
        return {
            "topo_confidence_score": 0.0,
            "geometry_score": 0.0,
            "render_mode": RENDER_MODES["SUPPRESSED"],
            "reason": f"Insufficient spatial density ({n_sensors}/{MIN_TOPO_CHANNELS} clean sensors)"
        }

    # 2. Geometry & Spread Score
    points = np.array([[s["x"], s["y"]] for s in eligible_sensors])
    x_range = np.max(points[:, 0]) - np.min(points[:, 0])
    y_range = np.max(points[:, 1]) - np.min(points[:, 1])
    
    # Normalized spread (ideal 10-20 spans approx 2.0 units in X and Y)
    spread_score = min(1.0, (x_range * y_range) / 3.0) 
    
    # Symmetry Score (how centered is the sensor cloud?)
    mean_x = np.mean(points[:, 0])
    symmetry_score = max(0.0, 1.0 - abs(mean_x) * 2) # Penalize lateral lean
    
    # Excluded sensor penalty
    exclusion_ratio = (total_requested - n_sensors) / max(total_requested, 1)
    exclusion_penalty = min(0.3, exclusion_ratio * 0.5)
    
    # Mean quality of sensors
    mean_quality = np.mean([s.get("quality", 100) for s in eligible_sensors]) / 100.0
    
    # Final Geometry Score
    # Weights: Spread (40%), Symmetry (30%), Distinct Regions (30%)
    region_score = min(1.0, distinct_regions / 5.0)
    geometry_score = (spread_score * 0.4) + (symmetry_score * 0.3) + (region_score * 0.3)
    geometry_score = max(0.0, geometry_score - exclusion_penalty)
    
    # Final Topo Confidence Score
    topo_confidence_score = (geometry_score * 0.7) + (mean_quality * 0.3)
    
    # 3. Render Mode Selection
    render_mode = RENDER_MODES["FULL"]
    
    if topo_confidence_score < 0.3:
        render_mode = RENDER_MODES["SUPPRESSED"]
    elif topo_confidence_score < 0.5 or distinct_regions < 3:
        render_mode = RENDER_MODES["LIMITED"]
    elif topo_confidence_score < MIN_GEOMETRY_SCORE_FOR_FULL_RENDER:
        render_mode = RENDER_MODES["CAUTIOUS"]
        
    return {
        "topo_confidence_score": float(topo_confidence_score),
        "geometry_score": float(geometry_score),
        "spatial_spread": float(spread_score),
        "symmetry_score": float(symmetry_score),
        "distinct_regions": distinct_regions,
        "usable_channel_count": n_sensors,
        "render_mode": render_mode
    }
