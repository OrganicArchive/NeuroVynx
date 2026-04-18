# Safety & Scope — Interpretive Boundaries

## Scope Statement

NeuroVynx is a **research-focused EEG and quantitative EEG (qEEG) framework**. It is designed as a software platform for signal processing exploration, method development, and research-oriented education. This framework is intended to support exploratory and methodological research rather than validated clinical workflows.

**NeuroVynx is NOT a medical device.** It has not been reviewed or cleared by the FDA, EMA, or any other regulatory body for clinical use.

## Non-Diagnostic Policy

The NeuroVynx framework and its associated outputs are strictly **non-diagnostic**. 
-   **Descriptive Analysis**: All analytical outcomes (e.g., band power, topography, Z-scores) are descriptive mathematical representations of the underlying EEG signal.
-   **Reference-Based Interpretation**: Normative layers and Z-score maps express deviation relative to a specific reference group only. They do not indicate health, disease, or pathology.
-   **Terminology**: This project explicitly avoids clinical or pathological labels. Terms like "abnormal," "epileptiform," "diseased," or "pathological" are not supported by the framework's logic.

## Trust-Gating Philosophy

A core safety feature of NeuroVynx is **trust-aware gating**. 
-   If signal quality (as determined by the Quality Engine) falls below a predefined threshold, the system is designed to **withhold comparative analysis**.
-   This "fail-silent" approach is intentional; it prevents the presentation of neural inferences based on noise or artifact-contaminated data.

## Supported vs. Unsupported Use Cases

### Current Framework Support
-   Signal quality and artifact density estimation.
-   Spectral feature extraction (PSD, Band Power).
-   Spatial topography interpolation.
-   Statistical comparison against internal reference datasets (Z-scores).

### Unsupported (Out of Scope)
-   **Automated Disease Classification**: No "black box" diagnostic classifiers.
-   **Seizure/Epileptiform Detection**: Not validated for clinical spike/wave detection.
-   **Treatment Recommendation**: Cannot be used to recommend medications or therapies.
-   **Clinical Reporting**: Outputs are for research documentation, not clinical patient records.

## Normative Reference Disclosure

> [!WARNING]
> **Mock Normative Data**: The internal normative reference datasets provided in this repository are currently for **validation and architectural demonstration only**. They are not clinically validated normative samples and should not be used for significant research conclusions without replacing them with specialized reference groups.

## Research Use Disclaimer

NeuroVynx is intended for research, software engineering experimentation, and educational exploration only. All users are responsible for ensuring that their use of this software complies with local institutional review boards (IRB) and ethical standards for human subjects research.

---
*Safety First — Trust the Signal*
