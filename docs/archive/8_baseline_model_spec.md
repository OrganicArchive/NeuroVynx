# Baseline & Model Output Specification

## 1. Personalised Baseline Engine

Comparing an individual to population norms is rarely useful for wearable/cognitive EEG due to massive inter-subject anatomical variance. The system relies on **intra-subject baselining**.

### Creating a Baseline (Calibration)
1. User undergoes a controlled calibration session (e.g. "2 Minutes Resting Eyes Open", "2 Minutes Resting Eyes Closed").
2. The pipeline extracts **FeatureSets** for every 2-second window (e.g., Theta power in Fz, Alpha power in Pz, Asymmetry F3/F4).
3. The engine computes the **mean** ($\mu$) and **standard deviation** ($\sigma$) for each feature over the clean windows of the session.
4. Generates a `BaselineProfile` JSON object storing these stats.

### Scoring against a Baseline
1. During a new task session, a new FeatureSet vector $X$ is generated.
2. Calculate the Z-score for feature $i$: $Z_i = \frac{X_i - \mu_i}{\sigma_i}$.
3. UI presents these deviations. "Frontal Theta is +1.5 standard deviations above your baseline."

## 2. Explainable Analytics Schema

If the app outputs a cognitive state prediction (e.g. Fatigue), it MUST use the `ModelOutput` architecture to guarantee explainability.

**Fields**:
- `value`: (float) e.g., 0.82
- `label`: (string) e.g., "High Fatigue"
- `confidence`: (float 0-1) Model certainty.
- `explanation_json`: 
  ```json
  {
    "top_positive_drivers": [
      {"feature": "Relative Theta (Global)", "weight": 0.45},
      {"feature": "Delta/Alpha Ratio", "weight": 0.20}
    ],
    "top_negative_drivers": [
      {"feature": "Frontal Beta", "weight": -0.15}
    ]
  }
  ```
- `warning_json`: Will block or heavily caveat the output if artifact confidence is high or channel quality is low.
  ```json
  {
    "issues": ["Excessive blink artifacts in current window.", "O2 electrode dropout."],
    "remedy": "Result reliability lowered. Check participant connection."
  }
  ```

## 3. MVP AI Architecture Approach
- Start with **Scikit-learn** models (Logistic Regression, Random Forests, or simple Heuristics like Alpha/Theta ratios) rather than opaque Deep Learning models. Tree-based models provide feature importance natively, fulfilling the explainability requirement for the MVP.
