import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.database import get_db
from app.models.session import Session
import mne

router = APIRouter()

@router.post("/upload", status_code=201)
async def upload_eeg_file(
    file: UploadFile = File(...), 
    db: DBSession = Depends(get_db)
):
    if not file.filename.endswith(".edf") and not file.filename.endswith(".bdf"):
        raise HTTPException(status_code=400, detail="Only EDF/BDF files are currently supported")

    session_id = str(uuid.uuid4())
    
    # Ensure data dir exists
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    
    # Save the file locally
    safe_filename = f"{session_id}_{file.filename}"
    file_path = os.path.join(settings.DATA_DIR, safe_filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Validate file format and extract metadata using MNE-Python without eager loading
    try:
        raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
        duration = raw.times[-1] if len(raw.times) > 0 else 0
    except Exception as e:
        # If it fails, delete the invalid file and raise
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted EEG file: {str(e)}")

    # Store in database
    new_session = Session(
        id=session_id,
        filename=file.filename,
        file_path=safe_filename,  # Store only the filename for portability
        status="uploaded",
        duration_seconds=int(duration)
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "session_id": session_id,
        "filename": file.filename,
        "status": new_session.status,
        "duration_seconds": new_session.duration_seconds,
        "message": "File uploaded and validated successfully."
    }
