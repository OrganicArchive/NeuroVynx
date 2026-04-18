"""
NeuroVynx: FastAPI DSP Application Entry Point
===============================================

This server acts as a specialized Digital Signal Processing (DSP) worker. 
It exposes standard REST endpoints for large-scale EEG data exploration, 
leveraging binary header parsing and lazy-loading for constant memory performance.

Design Philosophy:
- Statelessness: No local file state outside of the standard EDF/BDF storage.
- Precision: Direct interface with MNE-Python for surgical binary manipulation.
- Asynchrony: Heavy math tasks (Spectral scans) are compartmentalized for UI responsiveness.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.models import session, baseline, artifact
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

# --- AUTO-REPAIR SCHEMA (Self-Healing) ---
# This ensures existing databases are upgraded without data loss
try:
    with engine.connect() as connection:
        # Check if meta_data column exists, if not add it
        connection.execute(text("ALTER TABLE baselines ADD COLUMN meta_data JSON"))
        # Re-ensure artifact_baselines table is created (create_all handles this, but we'll be explicit)
        connection.commit()
except Exception:
    pass

# Create the database tables
Base.metadata.create_all(bind=engine)

def seed_heuristic_artifacts(db: DBSession):
    """
    Injects conservative heuristic templates for Blink and Motion 
    if the library is empty.
    """
    from app.models.artifact import ArtifactBaseline
    
    count = db.query(ArtifactBaseline).count()
    if count == 0:
        print("[SEED] Injecting default heuristic artifact templates...")
        
        # 1. BLINK HEURISTIC
        blink = ArtifactBaseline(
            artifact_label="blink",
            source_type="heuristic",
            features={
                "global_summary": {
                    "frontal_posterior_delta_ratio": 5.0, # Characteristic frontal delta elevation
                    "mean_relative_delta": 0.6
                },
                "per_channel": {
                    "Fp1": {"relative_delta": 0.8, "max_slope": 100.0},
                    "Fp2": {"relative_delta": 0.8, "max_slope": 100.0}
                }
            },
            meta_data={"notes": "Heuristic template inspired by common EOG blink characteristics: frontal delta emphasis + sharp steep slope."}
        )
        
        # 2. GROSS MOTION HEURISTIC
        motion = ArtifactBaseline(
            artifact_label="motion",
            source_type="heuristic",
            features={
                "global_summary": {
                    "mean_variance": 5000.0,
                    "left_right_total_asymmetry": 0.4,
                    "mean_relative_delta": 0.4
                }
            },
            meta_data={"notes": "Heuristic template for Gross Motion: Detects widespread, high-amplitude, multi-channel instability consistent with body or electrode movement."}
        )
        
        db.add(blink)
        db.add(motion)
        db.commit()

# Run seed on boot
from app.core.database import SessionLocal
db = SessionLocal()
try:
    seed_heuristic_artifacts(db)
finally:
    db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the Real-Time EEG Platform MVP",
    version="1.0.0",
)

# Set up CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP, allow all or set to electron/vite dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import upload, session, baseline, artifact, plugins
from app.plugins.loader import init_plugin_system

# Initialize Plugin System
init_plugin_system()

@app.get("/", tags=["General"])
def root():
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "documentation": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "mode": "SQLite MVP active"
    }

app.include_router(upload.router, prefix=settings.API_V1_STR + "/eeg", tags=["EEG Ingestion"])
app.include_router(session.router, prefix=settings.API_V1_STR + "/sessions", tags=["Session Data"])
app.include_router(baseline.router, prefix=settings.API_V1_STR + "/baselines", tags=["Baselines"])
app.include_router(artifact.router, prefix=settings.API_V1_STR + "/artifacts", tags=["Artifact Library"])
app.include_router(plugins.router, prefix=settings.API_V1_STR + "/plugins", tags=["Plugins"])
