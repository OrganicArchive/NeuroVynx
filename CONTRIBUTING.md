# Contributing to NeuroVynx (EEG/qEEG Research Framework)

Thank you for your interest in contributing to the NeuroVynx framework! We welcome contributions that help improve the reliability, transparency, and extensibility of EEG/qEEG research tools.

## Our Philosophy

NeuroVynx is a **trust-aware research framework**. All contributions are expected to align with these core principles:

1.  **Trust Before Interpretation**: Features should prioritize signal quality and trust evaluation over increasing metric count.
2.  **Non-Diagnostic Framing**: Avoid clinical, pathological, or diagnostic terminology. Use reference-based and descriptive language (e.g., "elevated relative to reference").
3.  **Modularity**: Keep the architecture decoupled. Backend logic should remain independent of frontend visualization where possible.
4.  **Transparency**: All DSP logic should be well-documented and mathematically transparent and verifiable.

## Code Standards

- Write clear, readable, and well-documented code.
- Document all DSP-related logic and equations where applicable.
- Avoid hard-coded thresholds without explanation.
- Keep functions modular and testable.
- Ensure compatibility with the existing pipeline structure.

## Review Expectations

All contributions are subject to review for:
- alignment with the project philosophy and safety constraints
- clarity and documentation quality
- impact on the integrity of the existing pipeline
- adherence to non-diagnostic and trust-aware design principles

## Ways to Contribute

- **Bug Reports**: File an issue detailing the environment and steps to reproduce.
- **Feature Proposals**: Discuss major architectural changes or new metrics in an issue first.
- **DSP Modules**: Implement new qEEG metrics or artifact detection heuristics.
- **Documentation**: Improve clarity, add examples, or refine the research-grade language.

## Contribution Workflow

1. **Open an Issue**: Discuss your proposed change to ensure it aligns with the project scope.
2. **Fork & Branch**: Create a feature branch from `main`.
3. **Implement & Test**: Ensure your changes do not break existing quality engines or pipelines.
4. **Submit a PR**: Provide a clear description of the change and its impact on the framework's research utility.

## Critical Proactive Safety Rules

- **No Diagnostic Overclaims**: Do not add "disease detectors," "automated diagnosis," or "clinical classification" modules.
- **Preserve Trust Gates**: Do not bypass signal quality checks to force analysis on low-quality data.
- **Research Only**: All new features must be explicitly marked as research-only in documentation and UI components where applicable.

## Scope Reminder

NeuroVynx is a research-focused EEG/qEEG framework and is not intended for clinical or diagnostic use. Contributions should not attempt to extend the system into validated medical or diagnostic domains.

---
*Questions? Open an issue or contact Kai Bakker : https://www.linkedin.com/in/kai-bakker-224746387/.*
