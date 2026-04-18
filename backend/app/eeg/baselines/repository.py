from sqlalchemy.orm import Session as DBSession
from app.models.baseline import Baseline

def save_baseline(db: DBSession, session_id: str, baseline_type: str, features: dict, metadata: dict = None, user_id: str = "default_user"):
    """
    Saves a new baseline. Overwrites the previous baseline of the same type for the user.
    """
    existing = db.query(Baseline).filter(
        Baseline.user_id == user_id, 
        Baseline.baseline_type == baseline_type
    ).first()
    
    if existing:
        existing.features = features
        existing.session_id = session_id
        if metadata is not None:
            existing.meta_data = metadata
        db.commit()
        db.refresh(existing)
        return existing
        
    new_baseline = Baseline(
        user_id=user_id,
        session_id=session_id,
        baseline_type=baseline_type,
        features=features,
        meta_data=metadata
    )
    db.add(new_baseline)
    db.commit()
    db.refresh(new_baseline)
    return new_baseline

def load_baseline(db: DBSession, user_id: str = "default_user", baseline_type: str = "resting"):
    """
    Loads the active baseline for a user.
    """
    return db.query(Baseline).filter(
        Baseline.user_id == user_id, 
        Baseline.baseline_type == baseline_type
    ).first()
