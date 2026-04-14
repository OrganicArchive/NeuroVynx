# Processing Pipeline Specification

The core DSP engine relies on Python (via MNE). For offline processing, or buffered online processing, the pipeline defines sequence blocks.

## Safety Rules
1. **Raw is immutable**: The ingestion system generates a `rawData` tensor. `pipeline.run()` generates a `processedData` tensor.
2. **Deterministic output**: Given the same raw input and the same DSP log parameters, the output must be identical.

## MVP Preprocessing Steps

When a "Preset" is run, the engine iterates through these steps if enabled in the preset:

### Step 1: Channel Drop & Rereference
- **Action**: Look at initial ChannelQuality scores. If an electrode has score < 10 (e.g., flatline), it is omitted from average-referencing to prevent corrupting the entire montage.
- **Rereference**: MNE `set_eeg_reference(ref_channels='average')` or specific (e.g. linked mastoids M1/M2).

### Step 2: Line Noise Removal
- **Method**: Notch filter. 
- **Parameter**: 50Hz (Europe/Asia) or 60Hz (Americas). Optional harmonics (100Hz, 120Hz).
- **Fallback**: MNE `filter.notch_filter`.

### Step 3: High-pass and Low-pass Bandpass Filtering
- **Method**: FIR Filter, windowed sinc. Zero-phase (filtfilt) to prevent temporal distortions.
- **Typical Range**: `1.0 Hz - 45.0 Hz`. (High pass at 1Hz removes slow drift and sweat artifact without needing extreme baseline correct; Low pass at 45Hz removes HF noise and line noise remnants).

### Step 4: Segmentation / Epoching (If task-based)
- **Method**: Slicing the continuous array into equal length windows.
- **Window Size**: 1.0s to 4.0s overlapping buffers for continuous real-time analysis, or event-locked epochs (-200ms to 800ms) if markers are present.

### Step 5: Artifact Mitigation (Module D Integration)
- **Action**: Depending on user setting, artifact "Events" found in the segment are handled.
- **Parameters**: 
  - `MARK_ONLY`: (Default) Do nothing to the data, just log it.
  - `INTERPOLATE_CHANNEL`: If one channel in a window is bad, interpolate using spherical spline from neighbors.
  - `REJECT_EPOCH`: Drop the window entirely from feature extraction.
  - `SUPPRESS_ICA`: (Post-MVP) Run FastICA, zero out the blinked component, reconstruct.

### Step 6: Baseline Correction (Task only)
- **Method**: Subtract mean of pre-stimulus interval from the epoch. 

## Log Serialization (Example)
```json
{
  "pipeline_run": [
    {"step": "DROP_FLAT", "channels_removed": ["Pz"]},
    {"step": "NOTCH", "freq": 50, "method": "fir"},
    {"step": "BANDPASS", "low": 1.0, "high": 45.0, "method": "fir"},
    {"step": "REREFERENCE", "ref": "average"}
  ]
}
```
