# UI Screen Plan & Wireframes

This document describes the layout and React Component composition for the primary MVP screens. The application should use a dark mode or high-contrast theme suitable for visual data analysis.

---

## Screen 1: Login / Workspace
**Purpose**: Landing zone, select who is using the app and which project.
- **Header**: Logo, Session Status.
- **Left Panel**: User selection list / Create new User.
- **Main Body**: Recent Sessions table (Date, User, Duration, Quality Score, Status).
- **Actions**: Large "New Session" button.

## Screen 2: New Session Setup
**Purpose**: Configure ingestion and parameters before raw data loads.
- **Wizard Flow**:
  1. **Source**: "Upload .edf" vs "Connect Live Stream".
  2. **Metadata**: Sample Rate, Hardware Model, Channel Montage verification.
  3. **Pipeline**: Select "Pipeline Preset" (e.g., Default Research vs Wearable Noisy).
  4. **Baseline**: Toggle "Enable Baseline Engine" and select Baseline Profile.
- **Confirm**: "Start Ingestion" -> transitions to Screen 3.

## Screen 3: Live Acquisition Dashboard (The Main Screen)
**Purpose**: The central nervous system of the application. See the data as it happens.
```text
+-------------------------------------------------------------+
| Header: Session Timer | Master Quality 92% | Rec/Stop Btn   |
+---------------------+---------------------------------------+
| Quality Panel       | +-----------------------------------+ |
| - Fp1: [GREEN] Good | |         EEG TRACES (Canvas)       | |
| - Fp2: [GREEN] Good | | Fp1: ~~~~/\~~~~~~/\~~~~           | |
| - C3:  [YELLOW] Warn| | Fp2: ~~~/  \~~~~/  \~~~           | |
| - C4:  [RED] Loose! | | C3:  ...flat..................... | |
|                     | | C4:  ~~/\/\/\/\/\/\/\/\/\/\/\~~~~ | |
| Action Req: C3 Flat | +-----------------------------------+ |
| Fix C4 Impedance!   | Event Markers Overlay  | Zoom/Pan   | |
+---------------------+---------------------------------------+
| Analytics Ticker    | Alert Log: [12:00:04] Blink (Fp1)     |
| Cognitive Load: 45% |            [12:00:15] Motion Warning  |
+---------------------+---------------------------------------+
```

## Screen 4: Signal Quality Detail Workflow
**Purpose**: Deep dive into why a channel is bad.
- **Metrics View**: Expanding a channel in the panel shows: Variance, 50/60Hz contamination ratio, Dropped Samples, Drift.
- **Recommendations View**: "Fp1 has high variance and blink-like morphology. Recommendation: Run ICA or ICA-based blink suppression pipeline."

## Screen 5: Cleaning Review (Post-Hoc View)
**Purpose**: Crucial requirement: Compare Raw vs Clean.
- **Split View**:
  - **Top Chart**: Raw Signal.
  - **Bottom Chart**: Cleaned Signal exactly temporally aligned.
- **Artifact Timeline**: A mini map at the bottom showing blocks of color denoting where artifacts were tagged. Clicking a block scrolls both viewers to that timestamp.
- **Approval Actions**: "Accept Pipeline Changes" or "Change Parameters & Rerun".

## Screen 6: Analytics Dashboard
**Purpose**: Feature analysis over long periods.
- **Trend Graphs**: Line charts of Alpha, Beta power over the session.
- **Baseline Matrix**: Radar chart comparing Current Session against User Baseline.
- **Explainability Panel**:
  ```text
  Estimate: FATIGUE 
  Confidence: 78% (Moderate)
  Main Drivers: 
   + Frontal Theta (Elevated +20%)
   - Posterior Alpha (Reduced -15%)
  Warning: O2 channel quality poor.
  ```

## Screen 7: Session Report Overview
**Purpose**: Auditability before final export.
- **Summary Cards**: Duration, Clean Data %, Artifact Events count.
- **Log Panel**: Verbatim step-by-step DSP log (e.g., 1. Notch 50Hz, 2. Bandpass 1-45Hz).
- **Export Control**: Buttons to download PDF, raw CSV, cleaned CSV, and JSON metadata.
