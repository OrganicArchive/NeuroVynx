# NeuroVynx: Known Limitations Registry

This document outlines the theoretical and empirical boundaries of the NeuroVynx Interpretive Intelligence engine. Understanding these limitations is essential for responsible research use.

## 1. Non-Diagnostic Intent
NeuroVynx is a **quantitative EEG (qEEG) research platform**. It is designed to track spectral variations and spatial patterns relative to normative and longitudinal baselines. 
> [!IMPORTANT]
> NeuroVynx is NOT a clinical diagnostic device. It does not identify clinical conditions, pathologies, or disorders. All findings should be interpreted secondary to raw waveform inspection by a qualified professional.

## 2. Montage & Geometry Dependence
- **Sparse Montages**: Interpretation confidence is automatically penalized when using fewer than 8 sensors. Spatial interpolation (Topography) becomes more speculative as sensor density decreases.
- **Electrode Placement**: Results assume standard 10-20 or 10-10 placement. Deviations in physical sensor location will result in inaccurate regional mapping.

## 3. Preprocessing Sensitivity
- The intelligence layer depends on the upstream quality of filtering (Bandpass/Notch).
- High residual noise (EMG, EOG) after filtering will trigger contradiction penalties and may cause legitimate neural signals to be suppressed if they overlap with artifact spectrums.

## 4. Normative Comparison Boundaries
- Normative Z-scores are calculated against age-matched reference groups.
- Findings reflect statistical distance, not clinical significance. A "Marked" deviation is a statistical outlier, not necessarily a pathological event.

## 5. Longitudinal Gating
- Comparison between sessions is blocked if channel montages, sampling rates, or preprocessing standards differ significantly.
- "No Reliable Change" may be reported if either session falls below quality thresholds, even if numerical differences exist.

## 6. Interpretive Silence (The "Suppression" Rule)
NeuroVynx is designed to be **conservative**. It will proactively suppress findings that lack multi-layer support (Spectral + Spatial + Temporal + Quality).
> [!TIP]
> Silence from the system often indicates insufficient evidence rather than the absence of a physiological phenomenon.
