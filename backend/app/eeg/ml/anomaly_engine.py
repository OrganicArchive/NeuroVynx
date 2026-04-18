import numpy as np
from typing import Dict, List, Any, Optional
from .clustering_engine import SimilarityEngine

class AnomalyEngine:
    """
    Identifies unusual EEG recordings or windows relative to a learned reference space.
    Focuses on 'surfacing' cases that deserve manual researcher review.
    """
    
    def __init__(self, version: str = "1.0-robust-zscore-anom"):
        self.version = version
        self.sim_engine = SimilarityEngine()

    def compute_anomaly_score(
        self, 
        current_vector: np.ndarray, 
        reference_library: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes a hybrid anomaly score based on distance to the library centroid 
         and nearest-neighbor rarity.
        """
        if not reference_library:
            return {"score": 0.0, "band": "low", "drivers": ["No reference library available"]}
            
        # Extract vectors from library
        library_vectors = np.array([case["pattern_vector"] for case in reference_library if "pattern_vector" in case])
        
        if len(library_vectors) == 0:
            return {"score": 0.0, "band": "low", "drivers": []}

        # 1. Centroid Distance (Global Anomaly)
        centroid = np.mean(library_vectors, axis=0)
        global_dist = np.linalg.norm(current_vector - centroid)
        
        # 2. Local Outlier Factor (Simplified - Distance to nearest neighbor)
        dists = [np.linalg.norm(current_vector - v) for v in library_vectors]
        min_dist = min(dists)
        
        # 3. Score Normalization (Heuristic for this baseline)
        # Assuming values ~0.1-0.5 are 'normal', >1.0 is rare
        raw_score = (global_dist * 0.4) + (min_dist * 0.6)
        normalized_score = min(1.0, raw_score / 1.5)
        
        band = "low"
        if normalized_score > 0.8:
            band = "high"
        elif normalized_score > 0.5:
            band = "moderate"
            
        return {
            "score": float(normalized_score),
            "band": band,
            "drivers": self._extract_anomaly_drivers(current_vector, centroid)
        }

    def _extract_anomaly_drivers(self, current_vec: np.ndarray, centroid: np.ndarray) -> List[str]:
        """Identifies which features deviate most from the reference mean."""
        drivers = []
        # Features index (from ClusteringEngine): 0-Delta, 1-Theta, 2-Alpha, 3-Beta, 4-Gamma, 5-RegAlpha, 6-RegBeta, 7-Qual
        feature_names = ["Delta power", "Theta power", "Alpha power", "Beta power", "Gamma power", "Regional alpha", "Regional beta", "Quality score"]
        
        diffs = np.abs(current_vec - centroid)
        top_diff_indices = np.argsort(diffs)[-2:] # Top 2 drivers
        
        for idx in top_diff_indices:
            if diffs[idx] > 0.15: # Significant deviation threshold
                direction = "elevated" if current_vec[idx] > centroid[idx] else "reduced"
                drivers.append(f"Unusual {feature_names[idx]} ({direction} relative to reference)")
                
        return drivers
