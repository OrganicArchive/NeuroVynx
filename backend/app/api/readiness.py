import os
import sqlite3
import mne
import numpy as np
import scipy
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from app.core.database import get_db, engine
from app.core.config import settings
from app.models.artifact import ArtifactBaseline
from app.models.session import Session

router = APIRouter()

@router.get("/status")
def get_system_status(db: DBSession = Depends(get_db)):
    """
    Returns a comprehensive diagnostic report of the current backend state.
    Filtered for privacy.
    """
    # 1. Database Inspection (Privacy Filtered)
    db_uri_raw = str(engine.url)
    db_file_name = os.path.basename(db_uri_raw.replace("sqlite:///", ""))
    
    db_file_size = 0
    if "sqlite" in db_uri_raw:
        path = db_uri_raw.replace("sqlite:///", "")
        if os.path.exists(path):
            db_file_size = os.path.getsize(path)

    # 2. Content Audit
    try:
        artifact_count = db.query(ArtifactBaseline).count()
        session_count = db.query(Session).count()
    except Exception as e:
        artifact_count = 0
        session_count = 0

    # 3. Environment Audit (Privacy Filtered)
    env_info = {
        "mne_version": mne.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "is_data_dir_writable": os.access(settings.DATA_DIR, os.W_OK) if os.path.exists(settings.DATA_DIR) else False
    }

    # 4. Normative Data Audit
    normative_path = os.path.join(settings.DATA_DIR, "eeg", "qeeg", "data", "normative_reference.json")
    
    return {
        "status": "online",
        "database": {
            "name": db_file_name,
            "file_size_bytes": db_file_size,
            "artifact_templates": artifact_count,
            "total_sessions": session_count
        },
        "environment_vitals": env_info,
        "normative_engine": {
            "is_ready": os.path.exists(normative_path)
        }
    }

@router.get("/integrity-check")
def run_integrity_check(db: DBSession = Depends(get_db)):
    """
    Verifies that the Core Knowledge Seed is applied.
    """
    from app.main import seed_core_knowledge
    seed_core_knowledge(db)
    
    artifact_count = db.query(ArtifactBaseline).count()
    return {
        "check": "complete",
        "templates_active": artifact_count
    }
