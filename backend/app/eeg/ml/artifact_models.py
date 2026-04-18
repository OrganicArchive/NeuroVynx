from typing import Dict, List, Any, Optional
from .artifact_features import get_feature_labels

class ArtifactClassifier:
    """
    Explainable baseline classifier for EEG artifacts.
    This version uses a heuristic-weighted threshold model as a placeholder 
    for the Logistic Regression / Random Forest baseline to establish the inference pipeline.
    """
    
    def __init__(self, model_id: str = "artifact_baseline_v1"):
        self.model_id = model_id
        self.version = "1.0.0"
        self.feature_labels = get_feature_labels()
        
    def predict_probas(self, features: Dict[str, Any]) -> Dict[str, float]:
        """
        Returns calibrated probabilities for multiple artifact classes.
        """
        probas = {}
        
        # 1. EMG Detection (HF dominant)
        hf_val = features.get("hf_power_mean", 0)
        # Probabilistic sigmoid-like mapping
        probas["emg_contamination"] = min(1.0, hf_val / 25.0) 
        
        # 2. Blink Detection (LF dominant)
        lf_val = features.get("lf_power_mean", 0)
        probas["blink_contamination"] = min(1.0, lf_val / 40.0)
        
        # 3. Electrode Dropout (Low variance)
        low_var_count = features.get("low_variance_channel_count", 0)
        probas["electrode_dropout"] = min(1.0, low_var_count / 4.0)
        
        return probas

    def get_drivers(self, label: str, features: Dict[str, Any]) -> List[str]:
        """Explains the top features contributing to a specific prediction."""
        drivers = []
        if label == "emg_contamination":
            if features.get("hf_power_mean", 0) > 10:
                drivers.append("Elevated high-frequency spectral components")
            if features.get("mean_slope", 0) > 5:
                drivers.append("Unstable trace slope")
        elif label == "blink_contamination":
            if features.get("lf_power_mean", 0) > 15:
                drivers.append("Prominent low-frequency frontal activity")
        elif label == "electrode_dropout":
            if features.get("low_variance_channel_count", 0) > 0:
                drivers.append("Flatline signatures detected in specific sensors")
                
        return drivers
