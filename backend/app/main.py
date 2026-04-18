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

def seed_core_knowledge(db: DBSession):
    """
    Injects sanitized core knowledge (artifacts/baselines) from the seed file.
    Only runs if the database is currently empty.
    """
    from app.models.artifact import ArtifactBaseline
    import json
    import os
    
    # Check if we've already seeded
    if db.query(ArtifactBaseline).count() > 0:
        return

    seed_path = os.path.join(os.path.dirname(__file__), "seeds", "core_knowledge.json")
    if not os.path.exists(seed_path):
        print(f"[SEED] Warning: Seed file not found at {seed_path}")
        return

    try:
        with open(seed_path, "r") as f:
            data = json.load(f)
            
        print(f"[SEED] Ingesting {len(data.get('artifact_baselines', []))} artifact templates...")
        for art in data.get("artifact_baselines", []):
            baseline = ArtifactBaseline(
                artifact_label=art["artifact_label"],
                source_type=art["source_type"],
                features=art["features"],
                meta_data=art["meta_data"]
            )
            db.add(baseline)
        
        db.commit()
        print("[SEED] Knowledge migration successful.")
    except Exception as e:
        db.rollback()
        print(f"[SEED] Error during migration: {e}")

# Run seed on boot
from app.core.database import SessionLocal
db = SessionLocal()
try:
    seed_core_knowledge(db)
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

from fastapi.responses import HTMLResponse

@app.get("/", tags=["General"], response_class=HTMLResponse)
def root():
    return """
    <html>
        <head>
            <title>NeuroVynx API</title>
            <style>
                body { font-family: 'Inter', sans-serif; background: #0f172a; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .card { background: #1e293b; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); text-align: center; border: 1px solid #334155; }
                h1 { color: #38bdf8; margin-bottom: 0.5rem; }
                p { color: #94a3b8; margin-bottom: 2rem; }
                .btn { background: #38bdf8; color: #0f172a; padding: 0.75rem 1.5rem; border-radius: 0.5rem; text-decoration: none; font-weight: bold; transition: opacity 0.2s; }
                .btn:hover { opacity: 0.9; }
                .links { margin-top: 2rem; display: flex; gap: 1rem; font-size: 0.875rem; }
                .links a { color: #64748b; text-decoration: none; }
                .links a:hover { color: #38bdf8; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>NeuroVynx Backend Active</h1>
                <p>The Analysis Engine is running successfully on Port 8000.</p>
                <a href="http://localhost:5173" class="btn">Go to Dashboard UI (Port 5173)</a>
                <div class="links">
                    <a href="/docs">API Documentation</a>
                    <span>&bull;</span>
                    <a href="/health">Health Status</a>
                </div>
            </div>
        </body>
    </html>
    """

from app.api import upload, session, baseline, artifact, plugins
from app.plugins.loader import init_plugin_system

# Initialize Plugin System
init_plugin_system()

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
