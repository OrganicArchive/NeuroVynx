from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base

class Baseline(Base):
    __tablename__ = "baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True) # Source session
    user_id = Column(String, index=True, default="default_user") # MVP single-user
    baseline_type = Column(String, default="resting") # e.g. "resting", "active"
    features = Column(JSON) # Storing the extracted features
    meta_data = Column(JSON, nullable=True) # Research-specific metadata (labels, timestamps, etc)
    created_at = Column(DateTime, default=datetime.utcnow)
