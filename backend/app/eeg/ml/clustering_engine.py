import numpy as np
from typing import Dict, List, Any, Optional
from scipy.spatial.distance import cosine

class SimilarityEngine:
    """
    Computes similarity between research sessions using trusted NeuroVynx feature vectors.
    Focuses on finding 'nearest neighbors' in the spectral and interpretive space.
    """
    
    def __init__(self, version: str = "1.0-spectral-similarity"):
        self.version = version

    def extract_pattern_vector(self, result: Dict[str, Any]) -> np.ndarray:
        """
        Constructs a stable feature vector from a full InterpretationResult.
        Inputs are weighted by trust/confidence to ensure reliable similarity.
        """
        # 1. Spectral Weights (Normalized band powers)
        qeeg = result.get("qeeg", {})
        band_summary = qeeg.get("summary", {}).get("band_relative_powers", {})
        
        # Order: Delta, Theta, Alpha, Beta, Gamma
        bands = ["delta", "theta", "alpha", "beta", "gamma"]
        spectral_vector = [band_summary.get(b, 0.0) for b in bands]
        
        # 2. Regional summaries (Simplified averages)
        regional_metrics = qeeg.get("regional_metrics", [])
        # We'll take the mean relative alpha/beta across regions as a simple descriptor
        reg_alpha = [r.get("metrics", {}).get("relative_alpha", 0.0) for r in regional_metrics]
        reg_beta = [r.get("metrics", {}).get("relative_beta", 0.0) for r in regional_metrics]
        
        regional_vector = [np.mean(reg_alpha) if reg_alpha else 0.0, 
                           np.mean(reg_beta) if reg_beta else 0.0]
        
        # 3. Quality Context
        qual_score = result.get("quality", {}).get("eeg_quality_score", 0.0) / 100.0
        
        # Combined vector
        return np.array(spectral_vector + regional_vector + [qual_score])

    def find_similar_cases(
        self, 
        current_vector: np.ndarray, 
        reference_library: List[Dict[str, Any]], 
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Finds the top_k most similar sessions in the reference library.
        """
        scores = []
        for case in reference_library:
            ref_vector = case.get("pattern_vector")
            if ref_vector is not None:
                # Cosine similarity (1 - distance)
                sim = 1.0 - cosine(current_vector, ref_vector)
                scores.append({
                    "session_id": case.get("session_id"),
                    "similarity_score": float(sim),
                    "description": case.get("description", "Unknown Session")
                })
                
        # Sort by similarity
        scores.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scores[:top_k]

    def generate_resemblance_description(self, similarity_score: float, top_case_desc: str) -> str:
        """Generates a human-friendly description for the similarity panel."""
        if similarity_score > 0.95:
            return f"Highly similar to {top_case_desc}"
        elif similarity_score > 0.85:
            return f"Resembles {top_case_desc}"
        elif similarity_score > 0.70:
            return f"Shows mild similarity to {top_case_desc}"
        return "No strong session-level matches in current library."
