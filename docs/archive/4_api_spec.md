# API Specification

MVP API definition using FastAPI (REST + WebSockets).

## REST Endpoints

### 1. Sessions Management
- **`POST /sessions/create`**
  Creates a new session context. Associates user, device, and expected metadata.
- **`POST /sessions/{id}/start`**
  Triggers status to active, arms the system for data ingestion.
- **`POST /sessions/{id}/stop`**
  Stops data ingestion and triggers finalize scripts.
- **`GET /sessions/{id}`**
  Fetches full session details.
- **`GET /sessions/{id}/report`**
  Generates and returns the PDF/JSON report bundle.

### 2. Device & Ingestion Management
- **`POST /devices/connect`**
  Initiates a direct stream connection (if using LSL/TCP).
- **`GET /devices/supported`**
  JSON list of supported hardware/formats.
- **`POST /upload/eeg`**
  Multipart form upload. Accepts a `.edf` file. Synchronously triggers data validation, returns `RawSignalFile` metadata.
- **`POST /stream/eeg-packet`**
  High-throughput endpoint for non-WS HTTP streaming (fallback).

### 3. Analytics & Quality Overviews
- **`GET /sessions/{id}/quality/live`**
  Returns rolling window arrays of ChannelQuality metrics.
- **`GET /sessions/{id}/artifacts/live`**
  Returns lists of recent ArtifactEvents.
- **`GET /sessions/{id}/features/live`**
  Returns recent FeatureSets.

### 4. Pipeline Engine
- **`POST /pipelines/run`**
  Runs specific preprocessing templates on a session. Body: `{"session_id": uuid, "preset_id": string}`.
- **`GET /pipelines/presets`**
  Lists available pipeline templates (Notch + Bandpass ranges, etc).
- **`POST /pipelines/save-preset`**
  Creates a custom sequence.

### 5. Baselines
- **`POST /baselines/create`**
  Trigger computation of a BaselineProfile from a designated session ID.
- **`GET /baselines/{user_id}`**
  Get user's baselines.
- **`POST /baselines/{user_id}/compare`**
  Submit a target Session ID to get deviation scores against an existing baseline.

### 6. Modeling & Export
- **`POST /models/run`**
  Trigger secondary ML models.
- **`GET /models/{session_id}/outputs`**
  Returns array of ModelOutputs.
- **`GET /exports/{session_id}/pdf`**, **`/csv`**, **`/json-log`**
  Downloads final derived data.

## WebSockets Channels
*(Essential for real-time frontend responsiveness)*

- **`/ws/session/{id}/trace`**
  Emits heavily down-sampled or windowed float arrays for plotting waveform lines on standard screens. 
- **`/ws/session/{id}/quality`**
  Emits boolean/string status changes per electrode (e.g., `{"Fp1": "BAD"}`).
- **`/ws/session/{id}/alerts`**
  Emits events: `{"type": "ARTIFACT_BLINK", "duration": 0.4}`.
- **`/ws/session/{id}/analytics`**
  Emits slow-frequency updates (e.g., 1Hz) with model outputs.
