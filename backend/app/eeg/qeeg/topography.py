"""
NeuroVynx: Topography Engine
===========================
Generates 2D scalp surface visualizations from discrete electrode measurements.

Mathematical Foundation: Shepard's Inverse Distance Weighting (IDW)
- Algorithm: Estimates values at unmeasured grid intersections as a weighted 
  average of all surrounding sensors.
- Weighting: Uses a power variable (p=2.0) where weights diminish with the 
  square of the distance (1/d^2), preserving high-frequency spatial gradients.
- Singularities: Implements an 'epsilon' buffer and sensor-snapping threshold 
  to prevent mathematical divergence at exact electrode locations.
- Boundary: Enforces a circular scalp mask (Masking) to eliminate extrapolation 
  artifacts outside the legitimate sensor array.
"""

import numpy as np
from scipy.interpolate import Rbf
from app.eeg.config.analysis_standards import (
    CANONICAL_BANDS, ELECTRODE_MAP, clean_name, 
    RENDER_MODES, TOPO_SUPPORT_RADIUS
)
from app.eeg.qeeg.topography_confidence import calculate_topo_fidelity

# Standard interpolation grid sizing
GRID_SIZE = 64

# Regional mapping for gating
REGIONS = {
    "Frontal": ["FP1", "FP2", "FPZ", "F7", "F3", "FZ", "F4", "F8"],
    "Central": ["C3", "CZ", "C4"],
    "Temporal": ["T7", "T3", "T8", "T4"],
    "Parietal": ["P7", "T5", "P3", "PZ", "P4", "P8", "T6"],
    "Occipital": ["O1", "OZ", "O2"]
}

def compute_band_topographies(channel_metrics, qeeg_trust_level):
    """
    Orchestrates the generation of 2D topographic grids for relative power bands.
    
    Validation Chain:
    1. Channel Filtering: Only includes sensors with 'trusted' or 'borderline' quality.
    2. Coverage Gating: Withholds interpolation if spatial density is too low for a 
       mathematically valid surface (minimum 6 channels across 3 regions).
    3. Grid Generation: 64x64 interpolated matrix with electrode recovery validation.
    """
    # 1. Collect Eligible Electrodes
    eligible_electrodes = []
    seen_points = set()
    distinct_regions = set()
    
    for ch in channel_metrics:
        raw_name = ch["channel"]
        name = clean_name(raw_name)

        if name in ELECTRODE_MAP:
            pos = ELECTRODE_MAP[name]
            if pos in seen_points: continue
            
            if ch["trust_level"] in ["trusted", "borderline"]:
                eligible_electrodes.append({
                    "name": name,
                    "x": pos[0],
                    "y": pos[1],
                    "metrics": ch["relative_power"],
                    "trust": ch["trust_level"]
                })
                seen_points.add(pos)
                
                for reg, labels in REGIONS.items():
                    if name in labels:
                        distinct_regions.add(reg)
                        break

    # 2. Coverage Fidelity Calculation (Phase 2)
    fidelity = calculate_topo_fidelity(
        eligible_sensors=eligible_electrodes,
        distinct_regions=len(distinct_regions),
        total_requested=len(channel_metrics)
    )
    
    # Suppression Gating
    if fidelity["render_mode"] == RENDER_MODES["SUPPRESSED"]:
        return {
            "is_available": False,
            "render_mode": fidelity["render_mode"],
            "reason": fidelity.get("reason", "Topographical support is too sparse for trust."),
            "topo_confidence_score": fidelity["topo_confidence_score"],
            "eligible_channel_count": len(eligible_electrodes)
        }

    # 3. Interpolation Settings
    grid_size = 64
    x_range = np.linspace(-1.1, 1.1, grid_size)
    y_range = np.linspace(-1.1, 1.1, grid_size)
    gx, gy = np.meshgrid(x_range, y_range)
    flat_gx = gx.flatten()
    flat_gy = gy.flatten()
    
    snap_threshold = 0.04
    epsilon = 1e-6
    idw_power = 2.0
    
    elect_x = np.array([e["x"] for e in eligible_electrodes])
    elect_y = np.array([e["y"] for e in eligible_electrodes])
    
    band_results = {}
    bands = ["delta", "theta", "alpha", "beta"]
    
    # Diagnostic channel groups
    FRONTAL_GRP = ["FP1", "FP2", "F3", "F4"]
    POSTERIOR_GRP = ["P3", "P4", "O1", "O2"]

    for band in bands:
        v = np.array([e["metrics"][band] for e in eligible_electrodes])
        v_min, v_max = float(np.min(v)), float(np.max(v))
        v_range = v_max - v_min
        
        low_variance_mode = v_range < 0.02
        
        # [DIAGNOSTIC] Basic Stats
        f_vals = [e["metrics"][band] for e in eligible_electrodes if e["name"] in FRONTAL_GRP]
        p_vals = [e["metrics"][band] for e in eligible_electrodes if e["name"] in POSTERIOR_GRP]
        
        f_mean = float(np.mean(f_vals)) if f_vals else 0.0
        p_mean = float(np.mean(p_vals)) if p_vals else 0.0
        ratio = p_mean / max(f_mean, 1e-6)
        
        dominance = "mixed_or_flat"
        if ratio > 1.2: dominance = "posterior_dominant"
        elif ratio < 0.8: dominance = "frontal_dominant"

        # Shepard's IDW Interpolation
        grid_values = np.zeros(flat_gx.shape)
        total_weights = np.zeros(flat_gx.shape)
        
        for j in range(len(flat_gx)):
            px, py = flat_gx[j], flat_gy[j]
            dists = np.sqrt((elect_x - px)**2 + (elect_y - py)**2)
            nearest_idx = np.argmin(dists)
            
            if dists[nearest_idx] < snap_threshold:
                grid_values[j] = v[nearest_idx]
                total_weights[j] = 1.0 
            else:
                w = 1.0 / (dists**idw_power + epsilon)
                grid_values[j] = np.sum(w * v)
                total_weights[j] = np.sum(w)
        
        interp_surface = grid_values / total_weights
        surface_2d = interp_surface.reshape((grid_size, grid_size))
        
        # [RECOVERY VALIDATION] Apply recovery check at electrode sensors in 2D grid
        recovery_errors = {}
        for i, e in enumerate(eligible_electrodes):
            # Find nearest grid coordinates
            ix = int(((e["x"] + 1.1) / 2.2) * (grid_size - 1))
            iy = int(((e["y"] + 1.1) / 2.2) * (grid_size - 1))
            # Accessing grid_size-1 clipped
            ix = max(0, min(grid_size-1, ix))
            iy = max(0, min(grid_size-1, iy))
            
            recovered_val = surface_2d[iy, ix] # In surface, rows are Y, cols are X
            error = abs(recovered_val - e["metrics"][band])
            recovery_errors[e["name"]] = float(error)

        # Mask logic (applies after recovery check)
        mask = (gx**2 + gy**2) <= 1.05
        surface_2d[~mask] = 0.0
        
        band_results[band] = {
            "surface": surface_2d.tolist(),
            "v_min": v_min,
            "v_max": v_max,
            "low_variance_mode": low_variance_mode,
            "render_mode": fidelity["render_mode"],
            "debug": {
                "frontal_mean": f_mean,
                "posterior_mean": p_mean,
                "posterior_frontal_ratio": ratio,
                "dominance_label": dominance,
                "recovery_errors": recovery_errors,
                "max_recovery_error": float(max(recovery_errors.values())) if recovery_errors else 0.0
            }
        }

    dominant_band = max(bands, key=lambda b: np.mean([e["metrics"][b] for e in eligible_electrodes]))
    
    # Topography Summary
    top_debug = band_results[dominant_band]["debug"]
    strongest_region = max(REGIONS.keys(), key=lambda r: np.mean([e["metrics"][dominant_band] for e in eligible_electrodes if e["name"] in REGIONS[r]]) if any(e["name"] in REGIONS[r] for e in eligible_electrodes) else 0)

    return {
        "is_available": True,
        "trust_level": qeeg_trust_level,
        "render_mode": fidelity["render_mode"],
        "topo_confidence_score": fidelity["topo_confidence_score"],
        "metric_type": "relative_power",
        "eligible_channel_count": len(eligible_electrodes),
        "distinct_region_count": len(distinct_regions),
        "summary": {
            "dominant_band": dominant_band,
            "strongest_region": strongest_region,
            "pattern_hint": f"{strongest_region} {dominant_band} dominance",
            "dominance_label": top_debug["dominance_label"]
        },
        "bands": band_results,
        "electrodes": [
            {"name": e["name"], "x": e["x"], "y": e["y"], "value": e["metrics"]}
            for e in eligible_electrodes
        ]
    }

def compute_normative_topography(normative_layer, qeeg_trust_level):
    """
    Generates 2D topographic maps for Normative Z-score deviations.
    
    Specialized Handling:
    - Zero-Anchored: Unlike relative power maps (which normalize to min/max), 
      Z-maps are anchored at zero (reference mean) to maintain clinical symmetry.
    - Diverging Scale: Supports visualization of signed deviations (elevations vs. reductions).
    """
    if not normative_layer.get("is_available") or not normative_layer.get("normative_allowed"):
        return {
            "is_available": False,
            "reason": normative_layer.get("reason", "Normative data or trust unavailable.")
        }

    topomap_layer = normative_layer.get("topomap_layer", {})
    if not topomap_layer.get("is_available"):
        return {
            "is_available": False,
            "reason": topomap_layer.get("reason", "Normative topography layer not eligible.")
        }

    import numpy as np # Ensure numpy is available in local scope if needed, though already imported globally

    # 1. Setup Interpolation
    grid_size = 64
    x_range = np.linspace(-1.1, 1.1, grid_size)
    y_range = np.linspace(-1.1, 1.1, grid_size)
    gx, gy = np.meshgrid(x_range, y_range)
    flat_gx = gx.flatten()
    flat_gy = gy.flatten()
    
    snap_threshold = 0.04
    epsilon = 1e-6
    idw_power = 2.0
    mask = (gx**2 + gy**2) <= 1.05

    band_results = {}
    bands = ["delta", "theta", "alpha", "beta"]
    norm_bands = topomap_layer.get("bands", {})

    # 2. Iterate Bands
    for band in bands:
        if band not in norm_bands:
            continue
            
        band_data = norm_bands[band]
        ch_scores = band_data["channel_z_scores"]
        
        # Collect coordinates for supported channels
        elect_x = []
        elect_y = []
        v = []
        
        for ch, z in ch_scores.items():
            name = clean_name(ch)
            if name in ELECTRODE_MAP:
                pos = ELECTRODE_MAP[name]
                elect_x.append(pos[0])
                elect_y.append(pos[1])
                v.append(z)

        if not v:
            continue
            
        elect_x = np.array(elect_x)
        elect_y = np.array(elect_y)
        v = np.array(v)

        # 3. IDW Interpolation (Signed)
        grid_values = np.zeros(flat_gx.shape)
        total_weights = np.zeros(flat_gx.shape)
        
        for j in range(len(flat_gx)):
            px, py = flat_gx[j], flat_gy[j]
            dists = np.sqrt((elect_x - px)**2 + (elect_y - py)**2)
            nearest_idx = np.argmin(dists)
            
            if dists[nearest_idx] < snap_threshold:
                grid_values[j] = v[nearest_idx]
                total_weights[j] = 1.0 
            else:
                w = 1.0 / (dists**idw_power + epsilon)
                grid_values[j] = np.sum(w * v)
                total_weights[j] = np.sum(w)
        
        interp_surface = grid_values / total_weights
        
        # 4. Hybrid Masking & Support Logic (Phase 2)
        # Defines the 'Spatial Truth' boundary.
        nearest_dists = np.zeros(flat_gx.shape)
        for j in range(len(flat_gx)):
            px, py = flat_gx[j], flat_gy[j]
            dists = np.sqrt((elect_x - px)**2 + (elect_y - py)**2)
            nearest_dists[j] = np.min(dists)
            
        # Support Envelope (1.0 close to sensors, fades to 0.0 at radius)
        # Handle the case where fidelity (for relative power) or general support (for normative) is sparse
        # For normative, we'll use a standard radius.
        mask_radius = TOPO_SUPPORT_RADIUS
        if 'fidelity' in locals() and fidelity["render_mode"] == RENDER_MODES["LIMITED"]:
            mask_radius *= 0.7
            
        support_envelope = np.clip(1.2 - (nearest_dists / mask_radius), 0, 1)
        interp_surface = interp_surface * support_envelope
        
        surface_2d = interp_surface.reshape((grid_size, grid_size))
        surface_2d[~mask] = 0.0

        band_results[band] = {
            "surface": surface_2d.tolist(),
            "z_min": band_data["z_min"],
            "z_max": band_data["z_max"],
            "symmetric_limit": band_data["symmetric_limit"]
        }

    return {
        "is_available": True,
        "trust_level": qeeg_trust_level,
        "map_type": "normative_z_map",
        "bands": band_results,
        "summary": {
            "pattern_hint": "Normative deviation topography available",
            "disclaimer": topomap_layer.get("disclaimer")
        }
    }
