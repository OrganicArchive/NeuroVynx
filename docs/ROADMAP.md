# Roadmap — NeuroVynx Framework

This roadmap outlines the past, present, and future trajectory of the NeuroVynx framework. Development is prioritized based on signal transparency, architectural stability, and framework utility.

## Development Philosophy

-   **Safety and Trust First**: Features are added conservatively. Logic that improves signal trust takes priority over raw feature count.
-   **Architecture-Led**: We prioritize "clean" modular code over rapid prototyping to ensure the framework remains reusable and extensible.
-   **Reproducibility Over Speed**: Development favors consistent, reproducible workflows over rapid feature expansion.

---

## Milestone 1: Foundation (Completed)
- [x] **Decoupled Architecture**: Separation of FastAPI backend and Electron/React frontend.
- [x] **Lazy EDF Loading**: Efficient handling of multi-hour EEG recordings.
- [x] **High-Performance Rendering**: Canvas-based waveform visualization.
- [x] **Core DSP**: Standard bandpass/notch filtering and metadata extraction.

## Milestone 2: Quality & Metrics (Completed)
- [x] **Heuristic Quality Engine**: Early detection of flatline, clipping, and high-variance noise.
- [x] **qEEG Metric Pipeline**: Power Spectral Density (PSD) and band power calculations.
- [x] **Temporal Minimap**: Navigation-ready artifact timeline.

## Milestone 3: Spatial & Normative (Completed / Active Extension)
- [x] **Spatial Topography Engine**: Interpolation and scalp mesh masking.
- [x] **Trust-aware normative comparison engine**: Signed Z-score computation against reference groups.
- [x] **Deviation Topography**: Zero-centered blue-white-red deviation maps.
- [ ] **Richer Baseline Support**: Ability to compare against multiple baseline sessions for a single subject.

## Milestone 4: Connectivity & Dynamics (Planned)
- [ ] **Connectivity metrics**: Implementation of coherence / PLV and Weighted Phase Lag Index (wPLI).
- [ ] **Advanced artifact decomposition**: Transitioning from heuristics to deep learning approaches (e.g., EEGNet) for artifact detection and signal decomposition.
- [ ] **Longitudinal subject tracking**: Visualizing metric evolution over months/years of research sessions.

## Milestone 5: Reporting & Integration (Future features)
- [ ] **Automated Research Summaries**: Generating structured JSON and PDF research summaries with non-diagnostic phrasing.
- [ ] **Plugin Architecture**: Enabling third-party researchers to "drop in" custom DSP modules.
- [ ] **Cloud-Bridge**: Optional PostgreSQL integration for large-scale multi-researcher datasets.

---
*A roadmap for trust-aware and reproducible EEG analysis*
