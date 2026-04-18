import numpy as np
from typing import Dict, List, Any
from .artifact_features import extract_artifact_features
from .artifact_models import ArtifactClassifier
from .clustering_engine import SimilarityEngine
from .anomaly_engine import AnomalyEngine
from ..qeeg.interpretation.models import MLArtifactPrediction, AdvisoryMLSection, ClusterMembership, AnomalyAlert

def run_ml_advisory(
    data_uv: np.ndarray, 
    sfreq: float, 
    channels: List[str],
    full_result_context: Optional[Dict[str, Any]] = None,
    research_mode: bool = False
) -> AdvisoryMLSection:
    """
    Orchestrates the secondary ML advisory layer.
    Extracts features and performs inference against baseline models.
    """
    if not research_mode:
        return AdvisoryMLSection(research_mode_active=False)
        
    # 1. Feature Extraction
    features = extract_artifact_features(data_uv, sfreq, channels)
    
    # 2. Classifier Inference
    classifier = ArtifactClassifier()
    probas = classifier.predict_probas(features)
    
    predictions = []
    for label, prob in probas.items():
        if prob > 0.3: # Advisory threshold
            conf_band = "high" if prob > 0.8 else "moderate" if prob > 0.5 else "low"
            drivers = classifier.get_drivers(label, features)
            
            predictions.append(MLArtifactPrediction(
                label=label,
                probability=float(prob),
                confidence_band=conf_band,
                drivers=drivers,
                advisory_status="secondary_signal"
            ))
            
    # 3. Similarity Discovery (Track B)
    cluster_member = None
    if full_result_context:
        sim_engine = SimilarityEngine()
        current_vec = sim_engine.extract_pattern_vector(full_result_context)
        
        # Mocking a reference library for initial implementation
        # In Phase 14-16 this would be loaded from a research baseline DB
        mock_library = [
            {"session_id": "ref_01", "description": "Normative alpha-dominant resting session", "pattern_vector": np.array([0.1, 0.1, 0.6, 0.15, 0.05, 0.6, 0.1, 0.9])},
            {"session_id": "ref_02", "description": "High-artifact low-SNR outlier", "pattern_vector": np.array([0.4, 0.2, 0.1, 0.2, 0.1, 0.1, 0.3, 0.2])}
        ]
        
        matches = sim_engine.find_similar_cases(current_vec, mock_library)
        if matches:
            best = matches[0]
            cluster_member = ClusterMembership(
                cluster_id="dynamic_pattern_01",
                membership_strength=best["similarity_score"],
                description=sim_engine.generate_resemblance_description(best["similarity_score"], best["description"]),
                similar_case_ids=[m["session_id"] for m in matches]
            )
            
    # 4. Anomaly Detection (Track C)
    anomaly_alerts = []
    if full_result_context:
        anomaly_engine = AnomalyEngine()
        current_vec = current_vec if 'current_vec' in locals() else SimilarityEngine().extract_pattern_vector(full_result_context)
        
        # We reuse the same mock library for anomaly comparison
        # (Is this session 'rare' relative to the library?)
        mock_library = [
            {"session_id": "ref_01", "description": "Normative alpha-dominant resting session", "pattern_vector": np.array([0.1, 0.1, 0.6, 0.15, 0.05, 0.6, 0.1, 0.9])},
            {"session_id": "ref_03", "description": "Standard adult resting record", "pattern_vector": np.array([0.12, 0.11, 0.55, 0.12, 0.04, 0.58, 0.12, 0.85])}
        ]
        
        anom_res = anomaly_engine.compute_anomaly_score(current_vec, mock_library)
        if anom_res["score"] > 0.5: # Moderate-to-high anomaly threshold
            anomaly_alerts.append(AnomalyAlert(
                target_id="session_current",
                anomaly_score=anom_res["score"],
                anomaly_band=anom_res["band"],
                likely_drivers=anom_res["drivers"],
                advisory_status="review_recommended"
            ))
            
    return AdvisoryMLSection(
        artifact_predictions=predictions,
        cluster_membership=cluster_member,
        anomaly_alerts=anomaly_alerts,
        model_version=classifier.version,
        research_mode_active=research_mode
    )
