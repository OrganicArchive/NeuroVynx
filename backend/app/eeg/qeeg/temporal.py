"""
NeuroVynx: qEEG Temporal Dynamics Module
========================================
This module provides time-resolved qEEG metrics by analyzing a rolling 
history of previously computed qEEG windows (typically up to 120s context).

Performance Metrics:
- Trend Classification: Uses Weighted Least Squares (WLS) regression to compute 
  slopes for band-pass power changes over time.
- Stability Index: Uses the Coefficient of Variation (CV = std/mean) to 
  quantify spectral noise and oscillation stability.
"""

from typing import List
import numpy as np

def compute_temporal_qeeg(history, current_qeeg, window_step=10.0):
    """
    Computes temporal trends and stability metrics from a history of qEEG results.
    
    Statistical Model:
    - Weighting: Observations are weighted by their interpretive confidence (Trusted vs Borderline).
    - Slope Derivation: Linear polyfit identifies the direction of power changes.
    - Consistency: Stability labels represent the dispersion of power values throughout the window chain.

    Args:
        history (list): List of past qEEG results (dictionaries).
        current_qeeg (dict): The current window's qEEG results.
        window_step (float): Time in seconds between window starts (Standard = 10s).
        
    Returns:
        dict: A validated temporal_qeeg object containing slopes, stability, and deltas.
    """
    # 1. Gather Total History Including Current
    full_history = history + [current_qeeg]
    
    # 2. Filter for Eligible Windows
    # Thresholds: EEG Quality >= 50, Confidence >= 50, Trust Level != unavailable
    eligible_windows = []
    for i, res in enumerate(full_history):
        # We need the quality/confidence info which is passed alongside qeeg typically
        # In our implementation, we'll assume the 'history' objects already contain 
        # the necessary power metrics.
        
        trust = res.get("trust_level", "unavailable")
        # Quality/Confidence check should have been done before adding to history
        # but we'll double check trust levels.
        if trust in ["trusted", "borderline"]:
            eligible_windows.append(res)
            
    # 3. Check Minimum History (Requirement: 4 windows for stable trend)
    if len(eligible_windows) < 4:
        return {
            "is_available": False,
            "reason": f"Acquiring temporal context: {len(eligible_windows)}/4 windows",
            "eligible_window_count": len(eligible_windows)
        }
        
    # 4. Extract Weights
    # Trusted = 1.0, Borderline = 0.5
    weights = np.array([1.0 if w["trust_level"] == "trusted" else 0.5 for w in eligible_windows])
    
    # 5. Global Band Trends
    # --------------------------------------------------------------------------
    bands = ["delta", "theta", "alpha", "beta"]
    global_trends = {}
    
    # Identify time points (relative to end)
    times = np.arange(len(eligible_windows)) * window_step
    
    for band in bands:
        values = np.array([w["summary"]["global_relative_power"][band] for w in eligible_windows])
        
        # Weighted Mean
        weighted_mean = np.average(values, weights=weights)
        
        # Weighted Slope (Least Squares)
        # We compute a simple linear fit y = mx + c
        # Reference: https://en.wikipedia.org/wiki/Weighted_least_squares
        # Using simple polyfit with weights
        try:
            coeffs = np.polyfit(times, values, 1, w=weights)
            slope = coeffs[0]
        except:
            slope = 0.0
            
        # Stability (Coefficient of Variation: std/mean)
        # Use weighted std if possible
        v_mean = np.average(values, weights=weights)
        v_var = np.average((values - v_mean)**2, weights=weights)
        std = np.sqrt(v_var)
        
        if v_mean > 0.001: # Avoid divide by zero
            cv = std / v_mean
        else:
            cv = 0.0
            
        # Stability Labels based on CV (Coefficient of Variation)
        stability_label = "high"
        if cv > 0.4: stability_label = "low"
        elif cv > 0.2: stability_label = "moderate"
        
        # Labels
        # Thresholds for slope: change > 0.0005 per second (~0.5% per 10s)
        slope_threshold = 0.0005 
        trend_label = "stable"
        if slope > slope_threshold: trend_label = "rising"
        elif slope < -slope_threshold: trend_label = "falling"
        
        # If variability is extremely high, label trend as variable
        if stability_label == "low":
            trend_label = "variable"
            
        global_trends[band] = {
            "current": values[-1],
            "rolling_mean": float(weighted_mean),
            "slope": float(slope),
            "trend": trend_label,
            "stability": stability_label,
            "cv": float(cv)
        }

    # 6. Window-to-Window Delta (Current vs Previous Trusted)
    # --------------------------------------------------------------------------
    window_delta = {}
    if len(eligible_windows) >= 2:
        curr = eligible_windows[-1]["summary"]["global_relative_power"]
        prev = eligible_windows[-2]["summary"]["global_relative_power"]
        
        for band in bands:
            abs_delta = curr[band] - prev[band]
            pct_delta = (abs_delta / (prev[band] + 1e-9)) * 100
            
            # Guard against percent-change bloat for tiny values
            if prev[band] < 0.01:
                pct_delta = None
                
            window_delta[f"{band}_change_abs"] = float(abs_delta)
            if pct_delta is not None:
                window_delta[f"{band}_change_pct"] = float(pct_delta)

    # 7. Overall Summary
    # --------------------------------------------------------------------------
    dominant_band = current_qeeg["summary"]["dominant_global_band"]
    dom_trend = global_trends[dominant_band]["trend"]
    
    # Calculate overall stability as average CV? Or worst CV?
    # Let's use average CV of the 4 bands
    avg_cv = np.mean([t["cv"] for t in global_trends.values()])
    overall_stability = "high"
    if avg_cv > 0.25: overall_stability = "low"
    elif avg_cv > 0.12: overall_stability = "moderate"

    summary = {
        "overall_stability": overall_stability,
        "dominant_temporal_pattern": f"{dom_trend} {dominant_band} dominance"
    }

    return {
        "is_available": True,
        "window_count_used": len(eligible_windows),
        "trusted_window_count": int(np.sum(weights == 1.0)),
        "borderline_window_count": int(np.sum(weights == 0.5)),
        "global_band_trends": global_trends,
        "regional_trends": [], # Phase 2A.2 placeholder
        "window_delta": window_delta,
        "summary": summary,
        "warnings": []
    }

