# Examples — Research Workflows

> [!NOTE]
> All workflows assume that signal quality thresholds and trust gating are respected. Results should always be interpreted in the context of signal reliability and reference selection.

## 1. Quality-Aware Signal Inspection

### Objective
Load an EEG recording and identify the most reliable segments for spectral analysis.

### Workflow
1.  **Ingest**: Navigate to the "Session Upload" dashboard.
2.  **Upload**: Select a standard `.edf` or `.bdf` file.
3.  **Audit**: Open the "Signal Viewer."
4.  **Minimap Scan**: Review the interactive timeline at the bottom of the screen.
    -   **Green Regions**: High signal trust. Suitable for qEEG analysis.
    -   **Yellow Regions**: Contextual artifacts (e.g., ocular blinks). The system will analyze these but with primary brain-signal trust reduced.
    -   **Red Regions**: Fatal technical noise (e.g., clipping or loose electrodes). The system will automatically gate analysis in these zones.

### Expected Output
-   A hierarchical breakdown of signal quality metrics.
-   Visual snapping to artifact-dense regions for validation.

---

## 2. Comparative qEEG Analysis

### Objective
Compare a subject's relative Alpha power against a normative reference group.

### Workflow
1.  **Stabilize**: Apply Notch (50 Hz) and Bandpass (1–45 Hz) filters using the top-bar controls.
2.  **Navigate**: Locate a high-quality (Green) 10-second segment using the timeline.
3.  **Metrics**: Review the "Spectral Analysis" sidebar. Observe the Relative Power distribution for standard bands (Delta, Theta, Alpha, Beta).
4.  **Reference**: Select the appropriate "Normative Reference Group" (e.g., "Age-Matched Adult Baseline").
5.  **Deviation Topo**: Inspect the "Normative Deviation Maps."

### Expected Interpretation (Reference-Based, Non-Diagnostic)
-   **Elevation**: "The Alpha power in the posterior region is **elevated relative to the reference group** (Z = +2.1)."
-   **Reduction**: "Beta activity across the frontal channels appears **reduced relative to the reference group** (Z = -1.5)."
-   **Within Range**: "Theta distribution is **within the expected reference range** (Z = +0.5)."

---

## 3. Handling Unavailable States

### Scenario: Low Trust Gating
If you navigate to a Red region (e.g., a massive movement artifact):
-   **System Behavior**: The Sidebar metrics and Normative Topography will transition to an **"Unavailable"** state with explanatory messaging.
-   **Reasoning**: "Analysis withheld due to insufficient signal trust."
-   **Corrective Action**: Navigate back to a Green or Yellow region to restore analysis.

### Scenario: Missing Metadata
If an EDF file is missing age or sex metadata required for a specific reference group:
-   **System Behavior**: The Normative dropdown will flag the mismatch.
-   **Corrective Action**: Manually update the session metadata in the "Session Settings" panel.

---
*NeuroVynx — Practical Workflows for Rigorous Science*
