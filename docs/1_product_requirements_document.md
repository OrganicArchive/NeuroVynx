# Product Requirements Document (PRD): Real-Time EEG Platform

## 1. Product Concept
A real-time EEG platform with intelligent signal-quality monitoring, artifact detection/removal, personalised baselines, explainable AI outputs, and reproducible reporting.

**Core Value Proposition**: "Turn raw noisy EEG into trustworthy, interpretable, real-time insights."

## 2. Target Audience
1. Researchers
2. Clinicians or supervised clinical teams
3. Neurofeedback / BCI developers
4. Advanced students / labs
5. Wearable EEG users

## 3. MVP Definitions & Success Criteria
**Objective**: Create a working desktop EEG app (Electron) capable of importing EEG files (.edf initially) and connecting to streams, calculating live signal quality, flagging bad channels, detecting artifacts, and storing data reliably.

**MVP Success Criteria**:
1. User can start a session in under 3 minutes.
2. App detects noisy electrodes in real-time.
3. App classifies >=4 artifact types (blinks, horiz eye, jaw/muscle, motion).
4. User can compare raw vs cleaned signal.
5. All processing steps logged and reproducible.
6. User can export session reports and processed data.

**Non-Goals for MVP**:
1. Full medical diagnosis.
2. Perfect source/deep-brain localisation.
3. Unsupervised clinical decision-making.

## 4. Core Modules
- **Module A - Data Ingestion**: File import (`.edf` for MVP) or live WebSocket stream. Dynamic channel map parsing.
- **Module B - Signal Viewer**: Performant multichannel canvas scrolling, channel health display.
- **Module C - Quality Engine**: Validates channel variances, flatlines, drift, high amplitude anomalies. Outputs score (0-100).
- **Module D - Artifact Intelligence**: Rolling window classification of blinks, motion, line noise. Confidence metrics attached to classifications.
- **Module E - Preprocessing**: Configurable standard pipeline (Notch -> Bandpass -> Bad Chan -> Interpolation -> Reref -> ICA/Artifact rejection).
- **Module F - Feature Extraction**: Band power (Alpha, Beta, Delta, Gamma, Theta), asymmetry, complexity.
- **Module G - Baseline Engine**: Compute user-specific baseline distributions, compare new sessions.
- **Module H - Explainable Analytics**: Heuristics for alertness, fatigue, and engagement with transparent drivers (e.g., "Elevated Theta vs Alpha").
- **Module I - Reporting**: Generate reproducible PDF and CSV session exports.

## 5. User Stories
- **Researcher**: "As a researcher, I want to import EEG and run a reproducible cleaning pipeline so that I can analyse data faster."
- **Clinician**: "As a clinician, I want the app to warn me which channels are unreliable so that I do not interpret bad data."
- **Wearable user**: "As a user, I want live feedback on electrode quality so that I can fix problems before recording too much noise."
- **Analyst**: "As an analyst, I want to compare raw and cleaned data so that I can trust the preprocessing."
- **Supervisor**: "As a supervisor, I want reports with clear logs so that I can audit exactly what happened."

## 6. Safety & Ethics
- Provide clear UI warnings: "This output is supportive analytics, not a diagnosis."
- Keep raw data strictly immutable. All cleaning is derived data.
- Ensure confidence scores accompany any intelligent classification.
