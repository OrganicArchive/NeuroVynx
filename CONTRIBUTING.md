# Contributing to NeuroVynx

Thank you for your interest in contributing to NeuroVynx! We are building a research-grade platform for EEG and qEEG analysis that prioritizes trust, transparency, and extensibility.

## Project Scope

NeuroVynx is a **Research and Educational Tool**. Contributions should align with:
- Improving signal processing fidelity.
- Enhancing visualization clarity.
- Developing transparent, confidence-aware analytical outputs.
- Maintaining the non-diagnostic boundaries of the platform.

## Ways to Contribute

### 1. Developing Plugins (Recommended)
Developing plugins is the easiest way to add new analytical or visualization capabilities without modifying the core codebase.
- See the [Plugin Development Guide](./docs/PLUGIN_GUIDE.md) for technical details.

### 2. Core Contributions
If you wish to modify the core DSP pipeline, API, or Dashboard:
1. **Fork the repository** and create a descriptive feature branch (e.g., `feat/`, `fix/`, `docs/`, `research/`, or `chore/`).
2. **Adhere to the architecture**: Review the [ARCHITECTURE.md](./docs/ARCHITECTURE.md) to understand the stateless, loop-driven design.
3. **Add tests**: Ensure new features are covered by unit tests in the `/backend/tests` or `/frontend/tests` directories.
4. **Submit a Pull Request**: Provide a clear description of the change and its scientific or technical rationale.

## Coding Standards

- **Python**: Follow PEP 8. Use type hints for all public APIs.
- **Frontend**: Use React with TypeScript. Prioritize functional components and Tailwind CSS for styling.
- **Documentation**: Update relevant Markdown files in the `/docs` folder for any architectural or functional shifts.

## Code of Conduct

All contributors are expected to uphold the [Code of Conduct](./CODE_OF_CONDUCT.md) to ensure a welcoming and professional environment.

## Scientific Integrity

NeuroVynx is used in research and educational settings. 
- Avoid implementing "black box" algorithms without thorough documentation of their parameters.
- Prioritize confidence scoring and quality flagging in all analytical outputs.
- Never implement diagnostic labels (e.g., "Parkinson's Detected") (keep outputs descriptive, e.g., "Increased beta-band variance noted in frontal channels").

---
Thank you for helping push the boundaries of transparent neuro-analysis!
