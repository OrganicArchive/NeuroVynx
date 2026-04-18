# NeuroVynx: Temporal Interpretation Guide

Expansion Phase 10 adds **Temporal Intelligence** to NeuroVynx, allowing it to reason about the stability and evolution of qEEG findings over time.

## 1. Classification Framework

The system classifies findings based on their recurrence across representative sampled windows (target = 8 windows).

| Classification | Meaning | Threshold |
| :--- | :--- | :--- |
| **PERSISTENT** | Findings are consistently observed across most of the recording. | >= 60% presence |
| **INTERMITTENT** | Findings appear significantly but are not constant. | >= 20% and < 60% presence |
| **TRANSIENT** | Findings are sporadic or single-excursion. | < 20% presence |
| **ARTIFACT-LINKED** | Findings coincide heavily with identified artifact contamination. | > 50% artifact overlap |
| **EVOLVING** | Findings show a measurable directional change in intensity or extent. | Slope-based (Experimental) |

## 2. Methodology: Representative Sampling

Instead of a full-file search (which is computationally expensive), NeuroVynx uses **Representative Sampling**:
1. It selects 8 candidate positions evenly spaced across the recording duration.
2. It executes the full window-level DSP and interpretation pipeline for each position.
3. Windows with extremely low confidence (< 0.2) are skipped, and caveats are recorded.
4. Insights are synthesized by aggregating findings across the usable windows.

## 3. Advanced Pattern Library

Phase 10 introduces richer pattern families that go beyond atomic band power clusters:

- **Regional Slowing**: Localized elevation of Delta/Theta (e.g., Frontal Slowing).
- **Alpha Organization**: Metrics for posterior alpha rhythm stability, asymmetry, and anteriorization.
- **Fast Activity**: Clustered Beta elevation.
- **Composite Patterns**: Synthesis of multiple families (e.g., Diffuse Slowing coupled with Alpha Reduction).

## 4. Safety & Claims

- **Non-Diagnostic**: The system describes temporal behavior (`persistently observed`) rather than diagnosing permanence.
- **Confidence-Aware**: Recording-level confidence is normalized by the number of usable windows sampled.
- **Transparency**: All skipped windows and skip reasons are exposed in the technical result.
