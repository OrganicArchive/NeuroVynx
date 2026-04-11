from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer

from app.core.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String) # Path to where the file is stored locally
    status = Column(String, default="created") # e.g. 'created', 'processing', 'completed', 'error'
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer, nullable=True) # Duration of the recording
    # More metadata will be extracted by MNE and populated here later
