from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Dict, Any, List

from app.core.database import get_db
from app.models.artifact import ArtifactBaseline

router = APIRouter()

class CreateArtifactRequest(BaseModel):
    artifact_label: str
    features: Dict[str, Any]
    metadata: Dict[str, Any] = None
    source_type: str = "calibrated"

@router.post("/create")
def create_artifact(req: CreateArtifactRequest, db: DBSession = Depends(get_db)):
    artifact_obj = ArtifactBaseline(
        artifact_label=req.artifact_label,
        features=req.features,
        meta_data=req.metadata,
        source_type=req.source_type
    )
    db.add(artifact_obj)
    db.commit()
    db.refresh(artifact_obj)
    return {"status": "success", "artifact_id": artifact_obj.id, "label": artifact_obj.artifact_label}

@router.get("/list", response_model=List[Dict[str, Any]])
def list_artifacts(db: DBSession = Depends(get_db)):
    artifacts = db.query(ArtifactBaseline).all()
    # Manual serialization since it's an MVP
    return [{
        "id": a.id,
        "artifact_label": a.artifact_label,
        "source_type": a.source_type,
        "created_at": a.created_at,
        "features": a.features,
        "metadata": a.meta_data
    } for a in artifacts]
