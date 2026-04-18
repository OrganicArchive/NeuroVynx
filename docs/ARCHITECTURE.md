# Architecture — System Design & Data Flow

## System Overview

NeuroVynx is built on a largely stateless architecture designed for high-performance signal processing and responsive visualization. It separates the heavy Digital Signal Processing (DSP) from the interactive User Interface (UI).

### High-Level Architecture
-   **Frontend**: React (Vite) hosted within an Electron shell. Uses HTML5 Canvas for hardware-accelerated waveform and topography rendering.
-   **Backend**: FastAPI (Python) server. Handles all DSP logic, file I/O (MNE-Python), and statistical calculations.
-   **Communication**: RESTful API for session management and websocket-ready architecture for future streaming.

## Data Flow

1.  **File Ingestion**: The backend uses MNE-Python to parse EDF/BDF headers. Metadata is extracted to identify sampling frequency and channel names.
2.  **EEG Isolation**: Signals are filtered and selected to isolate standard 10–20 EEG channels from EOG or auxiliary sensors.
3.  **Quality Engine**: The `engine.py` runs a multi-heuristic scan over the signal to compute "trust scores" and detect artifact-dense regions.
4.  **Metric Computation**: The `pipeline.py` computes PSD and band power metrics (Welch method) for trust-validated segments.
5.  **Normative Resolution**: The `normative.py` resolves the appropriate reference group (e.g., age-matched) and computes signed Z-scores.
6.  **Spatial Interpolation**: Channel-level values (e.g., band power or Z-scores) are interpolated into a continuous scalp mesh grid.
7.  **UI Rendering**: The frontend receives the processed data (JSON) and renders waveforms (Canvas) and topography (geometric scalp mask).

## Major Modules

### Backend (Python)
-   `engine.py`: The Signal Quality Engine. Contains the logic for artifact detection and trust scoring.
-   `pipeline.py`: The orchestration layer for DSP metrics.
-   `normative.py`: The mathematics of comparative Z-scores and reference group handling.
-   `topography.py`: The spatial interpolation and coordinate-mapping engine.

### Frontend (TypeScript/React)
-   `SessionViewer.tsx`: The primary container for waveform and sidebar analytics.
-   `BrainTopomap.tsx`: The coordinate-driven canvas renderer for spatial maps.
-   `SignalTrace.tsx`: High-performance waveform rendering component.

## Design Decisions

-   **Zero-Phase Filtering**: We use forward-backward filtering to prevent temporal signal distortion, which is critical for preserving spatial fidelity in topographic representations.
-   **Strict EEG Isolation**: Ocular activity is detected (EOG) but explicitly excluded from primary EEG quality metrics to ensure the "brain score" is not penalized by blinks.
-   **Trust Gating**: Normative results are mathematically withheld if the Quality Engine returns a score below a certain threshold (e.g., < 0.2), preventing "garbage-in/garbage-out" analysis.
-   **Circular Geometric Masking**: The UI uses a strictly geometric scalp mask to decouple transparency from Z-score magnitude, ensuring blue (negative) Z-scores are as visible as red (positive) ones.

## Design Constraints

-   **Real-time responsiveness** for interactive exploration.
-   **Deterministic processing** for reproducibility.
-   **Clear separation** between computation and visualization layers.
-   **Safe handling** of low-quality or incomplete data.

These constraints guide architectural decisions throughout the system.

## Extension Points

Researchers can extend the framework at several points:
-   **New Metrics**: Add functions to `backend/app/eeg/metrics/` and update `pipeline.py`.
-   **Reference Data**: Add new JSON-based normative models to `data/normative/`.
-   **Custom Visualizations**: Create new React components that consume the pipeline's JSON output.

---
*A modular architecture for transparent and reproducible neural analysis*
