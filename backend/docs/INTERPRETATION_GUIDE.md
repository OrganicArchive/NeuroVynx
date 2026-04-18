# NeuroVynx: Interpretation Engine Developer Guide

This document outlines the logic, schemas, and wording rules for the **Interpretive Intelligence Layer** in NeuroVynx.

## 1. Overview
The Interpretation Layer is a downstream synthesis engine that converts qEEG metrics and normative deviations into structured findings and natural-language summaries. It is designed to be **conservative**, **uncertainty-aware**, and strictly **non-diagnostic**.

## 2. Confidence Engine
Located in `interpretation/confidence.py`.

### Penalty Rules
Interpretation confidence starts at 1.0 and is reduced by:
- **Coverage**: -0.2 for missing EEG channels.
- **Artifacts**: -0.15 for identified Blink/EOG contamination.
- **Signal Quality**: Directly influenced by the `confidence_score` from the heuristic quality engine.

### Levels
- **>= 0.80**: High Confidence
- **0.55 - 0.79**: Moderate Confidence
- **< 0.55**: Low Confidence

## 3. Findings Extraction
Located in `interpretation/rules.py`.

### Z-Score Thresholds (Locked)
- **|z| >= 1.5**: Mild Deviation
- **|z| >= 2.0**: Moderate Deviation
- **|z| >= 3.0**: Marked Deviation

### Severity Mapping
- Z-score signs are converted to "Elevated" vs "Reduced" relative to the reference group.

## 4. Pattern Synthesis
Located in `interpretation/patterns.py`.

### Logic
- **Clustering**: Findings are grouped by band and region.
- **Robustness**: Most patterns require at least 2 supporting findings before being called.
- **Suppression**: Patterns that overlap with low-confidence regions (e.g. frontal theta during blinks) are automatically flagged as `suppressed_due_to_artifact`.

## 5. Summary Generation
Located in `interpretation/summaries.py`.

### Wording Rules
| Confidence | Verb Phrase |
| :--- | :--- |
| **High** | "was observed" |
| **Moderate** | "appears present" |
| **Low** | "may be present, but confidence is limited" |

## 6. Output Schema
Defined in `interpretation/models.py`.
The engine returns an `InterpretationResult` containing:
- `confidence`: Granular trust scores.
- `findings`: List of individual deviations.
- `patterns`: Aggregated high-order observations.
- `summary`: Short, Detailed, and Bulleted NLP versions.
