# Project Overview (NeuroVynx Framework)

## Project Motivation

NeuroVynx was developed to address a critical gap in EEG/qEEG analysis software: the disconnect between raw signal processing and interpretive confidence. Many existing tools provide advanced metrics, but fail to communicate the "trustworthiness" of the underlying signal. NeuroVynx introduces a framework in which signal quality is not merely a preprocessing step, but an integral component of the interpretation process.

## Conceptual Vision

NeuroVynx is envisioned as:
1.  **A Research Framework**: A modular environment for developing and testing new EEG/qEEG analytic methods.
2.  **A Reusable Pipeline**: A decoupled backend that can be integrated into various research ecosystems.
3.  **A Foundation**: A starting point for advanced neuroanalytic modules like connectivity, source localization, and longitudinal tracking.

## Major Functional Layers

### 1. Quality Engine
The first gate of the framework. It uses heuristic-based signal evaluation (variance, absolute amplitude, smoothness, and inter-channel coupling) to score the "trustworthiness" of each EEG segment. It differentiates between fatal technical failures and physiological artifacts.

### 2. qEEG Metrics Engine
Computes standard architectural metrics including Power Spectral Density (PSD), relative/absolute band power (Delta, Theta, Alpha, Beta), and regional ratios.

### 3. Plugin Governance System
A modular extension layer that allows for trust-tiered analytical and visualization plugins. 
- **Core Certified**: High-trust plugins integrated into primary narratives.
- **Unverified Local**: Secondary research plugins rendered in isolated "Plugin Insights" panels to prevent trust dilution of core outputs.

### 4. Interpretive Intelligence Layer
A hardened synthesis engine that generates confidence-aware narratives. It explicitly handles missing data, low-quality segments, and skipped analysis stages, ensuring the user is never presented with silent failures or unjustified conclusions.

### 5. Multi-modal Ready Foundation
While primarily focused on EEG, the data layer and dashboard are built with a generic temporal orchestration model. This allows for future expansion into simultaneous heart-rate (ECG), movement (Actigraphy), or context tracking without fracturing the core architecture.

### 6. Relational Topography
Visualizes Z-score deviations using a zero-centered diverging color scale (Developmental Score) or high-fidelity Relative Power maps. Includes automatic scale adjustment and normative gating based on subject age and recording state.

## System Pipeline Overview

The NeuroVynx pipeline follows a structured sequence:

1.  EDF ingestion and channel validation  
2.  EEG channel isolation and preprocessing  
3.  Signal quality evaluation (trust gating)  
4.  Spectral analysis and qEEG metric computation  
5.  Temporal tracking and regional aggregation  
6.  Spatial interpolation and topographic rendering  
7.  Normative reference selection (if available)  
8.  Z-score computation and deviation mapping  
9.  UI rendering with trust-aware gating and safe output states  

This structured pipeline ensures that all downstream analysis is contingent on signal integrity and available reference context.

## Design Philosophy

-   **Trust Before Interpretation**: No analysis is presented without a corresponding quality assessment.
-   **Reference-Based, Non-Diagnostic**: Outputs describe how data differs from a reference, not what that difference means clinically.
-   **Transparent Unavailable States**: If signal quality is low or reference data is missing, the system explicitly withholds analysis rather than presenting unreliable results.
-   **Modularity**: Clear separation between DSP pipeline, API layer, and UI renderer.
-   **Reproducibility**: The pipeline is designed to support consistent and repeatable EEG analysis workflows across datasets and environments.

## Intended Use Cases

-   **Research Prototyping**: Developing and validating new qEEG metrics.
-   **Educational Exploration**: Teaching EEG signal properties and qEEG fundamentals.
-   **Comparative Method Development**: Benchmarking different normalization or referencing strategies.
-   **Standardized Processing**: Applying a consistent analysis pipeline across research datasets.

## Not Intended Use Cases

- **Clinical Diagnosis**: NeuroVynx is not a diagnostic tool for neurological or psychiatric disorders.
- **Seizure Management**: It is not validated for acute seizure detection or patient monitoring.
- **Medical Decision Support**: It should not be used to guide treatment plans or surgical interventions.

---
*NeuroVynx: A trust-aware foundation for transparent, reproducible, and extensible neuro-analytics*
