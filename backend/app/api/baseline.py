from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Dict, Any

from app.core.database import get_db
from app.eeg.baselines.repository import save_baseline, load_baseline
from app.eeg.baselines.engine import compare_to_baseline

router = APIRouter()

class CreateBaselineRequest(BaseModel):
    session_id: str
    baseline_type: str = "resting"
    features: Dict[str, Any]
    metadata: Dict[str, Any] = None

class CompareBaselineRequest(BaseModel):
    features: Dict[str, Any]

@router.post("/create")
def create_baseline(req: CreateBaselineRequest, db: DBSession = Depends(get_db)):
    baseline_obj = save_baseline(db, req.session_id, req.baseline_type, req.features, req.metadata)
    return {"status": "success", "baseline_id": baseline_obj.id, "type": baseline_obj.baseline_type}

@router.get("/{user_id}")
def get_user_baseline(user_id: str, baseline_type: str = "resting", db: DBSession = Depends(get_db)):
    baseline_obj = load_baseline(db, user_id, baseline_type)
    if not baseline_obj:
        raise HTTPException(status_code=404, detail="Baseline not found")
        
    return {
        "id": baseline_obj.id,
        "session_id": baseline_obj.session_id,
        "type": baseline_obj.baseline_type,
        "created_at": baseline_obj.created_at,
        "features": baseline_obj.features,
        "metadata": baseline_obj.meta_data
    }

from app.models.artifact import ArtifactBaseline

@router.post("/{user_id}/compare")
def compare_baseline(user_id: str, req: CompareBaselineRequest, baseline_type: str = "resting", db: DBSession = Depends(get_db)):
    baseline_obj = load_baseline(db, user_id, baseline_type)
    if not baseline_obj:
        raise HTTPException(status_code=404, detail="Baseline not found for comparison")
        
    # Fetch artifact library for confidence calculation
    artifact_baselines = db.query(ArtifactBaseline).all()
        
    comparison = compare_to_baseline(req.features, baseline_obj.features, artifact_baselines)
    return comparison
