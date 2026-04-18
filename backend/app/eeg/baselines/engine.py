from app.eeg.baselines import classifier

def compare_to_baseline(current_features: dict, baseline_features: dict, artifact_baselines: list = None):
    """
    Compares a newly extracted feature set to a stored baseline feature set.
    Includes artifact-aware confidence scoring and interpretation.
    """
    deviations = {
        "per_channel": {},
        "global_summary": {}
    }
    
    interpretations = []
    
    # --- ARTIFACT & CONFIDENCE ANALYSIS ---
    artifact_label = None
    artifact_score = 0.0
    artifact_scores = {}
    confidence = 1.0
    
    if artifact_baselines:
        artifact_label, artifact_score, artifact_scores = classifier.score_artifact_match(
            current_features, artifact_baselines
        )
        confidence = classifier.calculate_interpretation_confidence(artifact_scores)
    
    # 1. Compare global summaries
    curr_global = current_features.get("global_summary", {})
    base_global = baseline_features.get("global_summary", {})
    
    for key, curr_val in curr_global.items():
        if key in base_global:
            base_val = base_global[key]
            
            # Prevent div by zero
            if base_val == 0:
                perc_dev = 0
            else:
                perc_dev = ((curr_val - base_val) / base_val) * 100.0
                
            deviations["global_summary"][key] = {
                "current": curr_val,
                "baseline": base_val,
                "percent_deviation": perc_dev
            }
            
            # Simple interpretations for major bands
            if abs(perc_dev) > 20.0 and "mean" in key:
                band_friendly = key.replace("mean_relative_", "Relative ").replace("mean_", "Absolute ")
                direction = "higher" if perc_dev > 0 else "lower"
                
                msg = f"{band_friendly.title()} power is {abs(perc_dev):.1f}% {direction} than baseline."
                
                # Confidence annotation
                if confidence < 0.8:
                    msg += " (Interpretation transparency reduced due to artifact detection)"
                
                interpretations.append(msg)

    # 2. Compare per-channel metrics (just high level)
    curr_ch = current_features.get("per_channel", {})
    base_ch = baseline_features.get("per_channel", {})
    
    outlier_channels = []
    
    for ch, metrics in curr_ch.items():
        if ch in base_ch:
            deviations["per_channel"][ch] = {}
            # We'll just look at peak_to_peak as a quick health dev
            curr_ptp = metrics.get("peak_to_peak", 0)
            base_ptp = base_ch[ch].get("peak_to_peak", 1) # safe div
            
            ptp_dev = ((curr_ptp - base_ptp) / base_ptp) * 100.0
            deviations["per_channel"][ch]["peak_to_peak_deviation"] = ptp_dev
            
            if abs(ptp_dev) > 50.0:
                outlier_channels.append(ch)

    if outlier_channels:
        if len(outlier_channels) > 5:
            interpretations.append("Multiple channels show significant structural deviation from baseline.")
        else:
            interpretations.append(f"High structural deviation on channels: {', '.join(outlier_channels)}")
    else:
        interpretations.append("All channels structurally within normal baseline range.")
        
    # Summary of artifacts in interpretation
    if artifact_label and artifact_score > 0.6:
        label_nice = artifact_label.replace("_", " ").title()
        interpretations.insert(0, f"DETECTED ARTIFACT: {label_nice} Likely (Match: {artifact_score*100:.0f}%)")

    return {
        "deviation_scores": deviations,
        "interpretation": interpretations,
        "artifact_data": {
            "best_match": artifact_label,
            "match_score": artifact_score,
            "all_scores": artifact_scores,
            "comparison_confidence": confidence
        }
    }
