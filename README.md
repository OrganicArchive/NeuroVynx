# NeuroVynx: High-Fidelity, Research-Oriented EEG Analysis Platform

> **Project Summary:**  
> NeuroVynx v0.1.0 is a complete research-grade prototype for a high-fidelity EEG analysis platform. It detects and classifies common EEG artifacts using feature-based matching and integrates **artifact-aware interpretation**, dynamically adjusting confidence in neural comparisons based on detected signal contamination.

> [!IMPORTANT]
> **Research Disclaimer**: NeuroVynx is a research-oriented EEG analysis platform and is not a certified medical device. It is intended for exploratory research and standardized dataset exploration and is not suitable for medical or diagnostic use. **Artifact detection is probabilistic and does not guarantee complete separation of neural and non-neural signals.**

---

## What It Does

NeuroVynx allows users to load large EEG recordings (EDF/BDF formats) and explore high-resolution multi-channel brainwave data efficiently without memory bottlenecks.

Using lazy loading and a decoupled architecture, only the required signal segments are streamed from disk, enabling smooth navigation across recordings ranging from seconds to multi-hour datasets.

In addition to visualization, NeuroVynx performs automated signal quality analysis, spectral feature extraction, and artifact detection to support rapid interpretation. The system incorporates **artifact-aware interpretation**, adjusting the confidence of neural analyses based on detected signal contamination.

---

## Why It Matters

Many EEG tools are either:
- computationally heavy research scripts, or  
- legacy desktop applications with poor performance  

NeuroVynx demonstrates a modern approach by combining:
- a high-performance React Canvas frontend  
- with a scientific Python DSP backend  

This results in a responsive system capable of handling real-world EEG data efficiently.

---

## Core Features

### EEG Data Handling
- Supports standard **EDF/BDF file ingestion**
- Near-instant metadata parsing via header extraction (MNE)
- Lazy loading ensures constant memory usage regardless of file size

### Visualization Engine
- Custom **HTML5 Canvas renderer** for high-performance waveform plotting
- Dynamic scaling for high-density EEG (64+ channels)
- Fixed 10-second window for consistent navigation

### Signal Processing (DSP)
- Bandpass filtering (1–45 Hz) and 50 Hz notch filtering
- Zero-phase filtering (forward-backward) to prevent signal distortion
- Sampling frequency-aware processing across different datasets

### Spectral Analysis
- Power Spectral Density (PSD) using Welch method
- Extraction of:
  - Delta
  - Theta
  - Alpha
  - Beta bands
- Computes absolute and relative power metrics

### Quality & Artifact Detection
- **Feature-driven, heuristic-based signal quality detection**:
  - Flatline signals (hardware issues)
  - High variance (loose electrodes)
  - Peak-to-peak clipping (movement artifacts)
  - Likely ocular artifacts based on frontal electrode activity

### Artifact Timeline (Minimap)
- Global scan using sliding window analysis
- Interactive timeline highlighting anomaly regions
- Instant navigation to flagged segments

### Baseline Comparison
- Stores baseline recordings
- Compares active EEG data against baseline metrics
- Flags deviations in neural activity

### Data Export
- Structured JSON/CSV export for further analysis

---

## Architecture & Tech Stack

### Frontend
- Electron  
- React (Vite)  
- TypeScript  
- TailwindCSS  
- HTML5 Canvas  

### Backend
- FastAPI (Python)  
- MNE-Python  
- NumPy / SciPy  
- SQLAlchemy  
- SQLite (local database)  

### Architecture Design
- Fully decoupled, stateless system  
- Frontend handles visualization only  
- Backend performs all signal processing and analysis  

---

## EEG-Specific Design Considerations

- Supports standard **10–20 electrode naming conventions**  
- Processes signals in **microvolts (µV)**  
- Handles varying **sampling frequencies** automatically  
- Includes basic **re-referencing strategies** (e.g., common average reference)  
- Applies **zero-phase filtering** to preserve signal integrity  

---

## Local Setup

Ensure Python 3.9+ and Node.js v18+ are installed.

```bash
git clone https://github.com/yourusername/NeuroVynx-eeg.git
cd NeuroVynx-eeg

make install-backend
make install-frontend
make bootstrap
make dev
```

## Guided Demo Checklist

To see NeuroVynx's full capabilities locally, follow this interactive checklist:

1. **Boot Environment**: Run `make dev` to fire both the Python Backend and React Frontend orchestrators.
2. **Upload EEG**: Navigate to the upload dashboard and import a standard `.edf`.
3. **Open Viewer**: Click "Open Signal Viewer" on the resulting success card.
4. **Use Timeline Navigation**: Look at the interactive minimap bounding the bottom of the screen. Click on a Yellow or Red segment bounding box to instantly snap the viewer to that chronological defect.
5. **Toggle DSP Filters**: Toggle the `Notch (50Hz)` and `Bandpass (1-45Hz)` filters at the top of the interface to visually clean the raw lines.
6. **Analyze Features**: Navigate to the Right sidebar and review the Alpha/Beta structural PSD proportions mapped dynamically over the 10-second slice.
7. **Export Report**: Trigger the API endpoint to securely export a flat JSON summary of the file parameters.

---

## Ethical / Research Disclaimer

> **NeuroVynx is a research-oriented EEG analysis platform and is not a certified medical device. This software is intended for research and educational purposes only.**

## Known Limitations
- Currently file-based, not live hardware streaming.
- Artifact detection logic is heuristic-based and probabilistic; it does not perform full signal decomposition or guaranteed artifact separation.
- Baseline workflow is purely local and mathematically simplified.
- Report export utilizes a bare JSON-first payload rather than native PDF rendering.

## Future Roadmap
- **Advanced Artifact Classification**: Moving from heuristics to deep learning models (e.g., EEGNet) for improved multi-class artifact separation.
- **Postgres Migration**: Shifting from localized SQLite binary blobs to cloud PostgreSQL containers.
- **Advanced Authentication**: Setting up remote researcher user pools.
- **Artifact ICA**: Leveraging Independent Component Analysis directly into the FastAPI wrapper to mathematically delete blink noise from the signal trace.

---
*The system emphasizes interpretability and transparency, ensuring that all analytical outputs are accompanied by confidence-aware explanations.*
*NeuroVynx integrates artifact-aware interpretation, ensuring that neural inferences are adjusted based on signal quality and artifact contamination.*
*Built as a functional architecture demonstration connecting modern web visualization paradigms to classic python digital signal processing.*
