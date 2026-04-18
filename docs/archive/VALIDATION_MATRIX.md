# NeuroVynx Validation Matrix (Phase 10)

This matrix documents the system performance across standardized synthetic EEG fixtures and multi-window temporal scenarios. All tests are automated via `backend/tests/test_validation.py` and `backend/tests/test_recording_analysis.py`.

## Artifact & Quality Detection

| Case ID | Goal | Status | Confidence | Detection Accuracy |
| :--- | :--- | :--- | :--- | :--- |
| **A: Clean** | Verify baseline purity | ✅ PASS | 98% (V.High) | 100% Correct Non-Detection |
| **B: Blinks** | Frontal eye-blink isolation | ✅ PASS* | 89% (High) | Detected: Blink/Transient |
| **C: Line Noise** | 50Hz environmental contamination | ✅ PASS* | 92% (High) | Detected: Broadband Contamination |
| **D: Unstable** | High noise floor robustness | ✅ PASS | 67% (Mod) | Correct channel preservation |

> [!NOTE]
> *PASS for Cases B and C indicates correct heuristic flagging, even if the interpretation summary remains focused on clinical findings.*

## Interpretative Pattern Synthesis

| Case ID | Targeted Pattern | Status | Key Findings Detected |
| :--- | :--- | :--- | :--- |
| **E: Diffuse Slowing** | Delta/Theta elevation | ✅ PASS | Widespread Slowing, Regional central pwr |
| **F: Alpha Reduc.** | Restricted posterior alpha | ✅ PASS | Posterior Alpha Reduction, Dominant Beta |
| **G: Mixed Case** | Daily messy segment | ✅ PASS* | 0 Patterns (Correct), 33% Quality |

## Temporal Dynamics & Persistence (Phase 10)

| Case ID | Targeted Stability | Status | Temporal Badge | Persistence Ratio |
| :--- | :--- | :--- | :--- | :--- |
| **H: Persistent Slow** | Continuous slowing across 5min | ✅ PASS | **PERSISTENT** | 100% |
| **I: Intermittent Alpha** | Alpha reduction in middle thirds | ✅ PASS | **INTERMITTENT** | 38% |
| **J: Transient Blink** | Sporadic blink bursts | ✅ PASS | **ARTIFACT-LINKED** | 100% overlap |
| **K: Evolving Trend** | Slope-aware change (Experimental) | 🚧 WIP | TBD | TBD |

## Validation Policy
1. **Trust-Gating**: Patterns are withheld if confidence < 60%.
2. **Artifact Suppression**: Frontal theta patterns are suppressed during blink detection.
3. **Temporal Sampling**: Recording-level summary requires >= 3 interpretable windows to form a conclusion.
4. **Conservative Claims**: Summaries lead with persistent findings first.

---
*Last Updated: 2026-04-17*
