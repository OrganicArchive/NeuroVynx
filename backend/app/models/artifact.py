from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base

class ArtifactBaseline(Base):
    """
    Stores reference 'templates' for identifying common EEG artifacts.
    Supports a hybrid model of built-in heuristics and user-specific calibrations.
    """
    __tablename__ = "artifact_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    artifact_label = Column(String, index=True)  # e.g., "blink", "motion", "jaw_clench"
    source_type = Column(String, default="calibrated")  # "heuristic" or "calibrated"
    
    features = Column(JSON)  # Extended feature vector (spatial, temporal, spectral)
    meta_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
