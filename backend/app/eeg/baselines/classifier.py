import numpy as np
from typing import List, Dict, Any

def score_artifact_match(current_features: Dict[str, Any], library_baselines: List[Any]):
    """
    Compares current segment features against the Artifact Library.
    Returns the best matching artifact label and a confidence reduction score.
    """
    best_match = None
    best_score = 0.0
    all_scores = {}
    
    curr_global = current_features.get("global_summary", {})
    curr_ch = current_features.get("per_channel", {})
    
    for artifact in library_baselines:
        label = artifact.artifact_label
        target_features = artifact.features
        target_global = target_features.get("global_summary", {})
        target_ch = target_features.get("per_channel", {})
        
        score = 0.0
        weight_sum = 0.0
        
        # 1. GLOBAL SPATIAL MATCH (High Weight)
        if "frontal_posterior_delta_ratio" in target_global and "frontal_posterior_delta_ratio" in curr_global:
            t_ratio = target_global["frontal_posterior_delta_ratio"]
            c_ratio = curr_global["frontal_posterior_delta_ratio"]
            
            # Use ratio of ratios, capped at 1.0
            ratio_match = min(c_ratio, t_ratio) / max(c_ratio, t_ratio + 1e-12)
            score += ratio_match * 5.0
            weight_sum += 5.0
            
        # 2. SPECTRAL PROFILE MATCH (Relative Delta/Alpha/etc)
        for band in ["delta", "theta", "alpha", "beta"]:
            key = f"mean_relative_{band}"
            if key in target_global and key in curr_global:
                t_val = target_global[key]
                c_val = curr_global[key]
                match = 1.0 - min(1.0, abs(t_val - c_val) / (t_val + 1e-12))
                score += match * 2.0
                weight_sum += 2.0
                
        # 3. VARIANCE MAGNITUDE (Medium Weight)
        if "mean_variance" in target_global and "mean_variance" in curr_global:
            t_var = target_global["mean_variance"]
            c_var = curr_global["mean_variance"]
            var_match = min(c_var, t_var) / max(c_var, t_var + 1e-12)
            score += var_match * 3.0
            weight_sum += 3.0

        # Normalize score to 0.0 - 1.0
        final_score = score / weight_sum if weight_sum > 0 else 0.0
        all_scores[label] = float(final_score)
        
        if final_score > best_score:
            best_score = final_score
            best_match = label
            
    return best_match, best_score, all_scores

def calculate_interpretation_confidence(artifact_scores: Dict[str, float]):
    """
    Calculates an adaptive confidence multiplier (0.0 to 1.0) based on 
    probabilistic artifact classification. 
    
    Confidence penalties scale linearly with the match strength to ensure 
    transparent reporting of signal contamination.
    """
    confidence = 1.0
    
    # Maximum penalty multipliers for different artifact classes
    MAX_PENALTIES = {
        "motion": 0.50,
        "muscle": 0.35,
        "blink": 0.30,
        "eye_movement": 0.25
    }
    
    for label, score in artifact_scores.items():
        # Adaptive penalty: Match Strength * Max Penalty
        penalty_limit = MAX_PENALTIES.get(label, 0.20)
        confidence -= (penalty_limit * score)
            
    # Clamp to ensure valid probability range
    return max(0.0, min(1.0, confidence))
