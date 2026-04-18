# NeuroVynx: Validation & Calibration Change Log

Track all changes to analysis thresholds, confidence offsets, and benchmark scoring rules.

## [2026-04-17] - Initial Calibration Pass
### Status: Baselines established
- **Threshold**: `CONFIDENCE_MIN_THRESHOLD` set to 0.4.
- **Reasoning**: Initial test runs showed that scores below 0.4 are consistently dominated by artifact-driven noise rather than identifiable neural rhythms.
- **Impact**: Increased suppression of artifact-heavy frontal recordings (Benchmark: `poor_quality_global_suppression`).

### Status: Contradiction Refinement
- **Action**: Reduced beta-elevation confidence penalty from 0.5 to 0.6.
- **Reasoning**: 0.5 was too aggressive, moving moderate elevations into 'blocked'. 0.6 preserves them in 'technical_only'.
- **Impact**: Improved audit visibility for potential muscle-noise overlap.

### Status: Temporal Gating
- **Action**: Persistence threshold for 'stable' classification set to 0.7.
- **Reasoning**: Standard for longitudinal research consistency.
- **Impact**: Calibrated against `stable_temporal_alpha` benchmark.
