# System Architecture

## Overview
The application uses a modern decoupled architecture. The frontend handles real-time visualization and user configuration, while a robust Python backend performs heavy DSP (Digital Signal Processing) and AI inference. 

## High Level Diagram

```mermaid
graph TD
    subgraph Frontend [Electron + React/Vite UI]
        UI[User Dashboard]
        Viewer[Performance Canvas Viewer]
        UI -->|Config & Commands| API[FastAPI Server]
        Viewer <-->|WS stream: EEG Packets & Alerts| WS[FastAPI WebSockets]
    end

    subgraph Backend [FastAPI Python Server]
        API --> DB[(PostgreSQL)]
        WS --> StreamBuffer[Rolling Stream Buffer]
        StreamBuffer --> Quality[Quality Engine (QC)]
        Quality --> Artifacts[Artifact Detection]
        Artifacts --> DSP[MNE Preprocessing Pipeline]
        DSP --> Features[Feature Extraction]
        Features --> Analytics[Explainable AI Analytics]
        
        Analytics --> WS
        Artifacts --> WS
        Quality --> WS
    end
    
    subgraph Storage Configuration
        DB --> Sessions[Session Metadata]
        DB --> Users[User/Baselines]
        ObjectStore[(File Storage)]
        ObjectStore -.->|Raw .edf files| StreamBuffer
        DSP -.->|Processed Data| ObjectStore
    end
    
    Hardware[EEG Hardware / Streamer] -.->|LSL / TCP / UDP| StreamBuffer
```

## Technology Stack

### Frontend
- **Wrapper**: Electron (Desktop-first deployment)
- **Framework**: React + TypeScript + Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Visualization**: HTML5 Canvas / WebGL (for 8+ channels at 250-1000Hz) or performant libraries like uPlot / LightningChart.

### Backend
- **Framework**: FastAPI (Python)
- **Signal Processing**: MNE-Python, SciPy, NumPy
- **Machine Learning**: Scikit-learn (MVP), PyTorch (Later)
- **Task Queues**: Celery or RQ + Redis (for heavy offline batch processing)

### Data & Persistence
- **Database**: PostgreSQL (Entities, session metadata, quality logs, user baselines)
- **File Storage**: Local file system (or S3 in cloud) for `.edf` files and processed outputs.
- **Cache/Stream State**: Redis (optional at MVP, for managing live streams across workers if scaling).

## Data Flow (Offline Analysis MVP)
1. User uploads an `.edf` file via the UI.
2. File is saved to local storage; Metadata (Session) is recorded in PostgreSQL.
3. User selects a pipeline preset and invokes processing.
4. FastAPI spins up a background worker task.
5. Rolling windows slice through the file data:
   - Quality engine generates per-epoch QC reports.
   - Artifacts are logged as events.
   - Feature bands are extracted.
6. The backend assembles these logs into a `ProcessedSignalFile` and `ArtifactEvent` lists.
7. Frontend reads logs and overlays artifacts/clean signals on the waveform viewer.

## North Star Rule
Raw data is IMMUTABLE. Any preprocessing runs create a separate logical stream/file, preserving absolute auditability.
