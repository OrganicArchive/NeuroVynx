# NeuroVynx Plugin Development Guide

NeuroVynx is designed with a **Plugin-Ready Architecture**, allowing researchers and developers to extend the core analytical loop without modifying the stable engine. Use this guide to create and integrate custom EEG analysis, visualizations, and imports.

## Directory Structure

Custom plugins should be placed in the `/plugins/local/` directory of the project root. Each plugin must have its own subdirectory:

```text
/plugins
  /local
    /my_custom_plugin
      manifest.json
      plugin.py
      ... (additional assets)
```

## 1. The Manifest (`manifest.json`)

Every plugin requires a `manifest.json` file in its root directory. This file identifies the plugin and its entry point.

```json
{
  "plugin_id": "com.example.psd_optimizer",
  "name": "PSD Optimizer",
  "version": "1.0.0",
  "category": "analysis",
  "entrypoint": "plugin.py",
  "description": "Adaptive power spectral density estimation.",
  "author": "NeuroLab",
  "trust_tier": "unverified_local"
}
```

### Manifest Fields
- `plugin_id`: A unique reverse-DNS style identifier.
- `category`: Must be one of `analysis`, `visualization`, `importer`, `normative`, or `workflow`.
- `trust_tier`: For local plugins, always use `unverified_local`. Official plugins use `core_certified`.

## 2. Implementing the Contract

NeuroVynx uses standard Python Base Classes (ABCs) as contracts. Your plugin's entrypoint must define a class that inherits from one of these contracts.

### Example: Analytics Plugin

```python
from app.plugins.contracts import AnalyticsPlugin
import numpy as np

class MyPsdPlugin(AnalyticsPlugin):
    def analyze(self, data_uv: np.ndarray, sfreq: float, channels: list[str]):
        # data_uv is a numpy array of shape (n_channels, n_samples)
        # Perform your math here...
        results = {
            "my_metric": 42.0,
            "status": "success"
        }
        return results
```

## 3. Trust and Output Separation

- **Certified vs. Experimental**: Output from `core_certified` plugins is integrated into the primary interpretation narrative. Output from `unverified_local` plugins is rendered in a dedicated **Plugin Insights** panel in the dashboard.
- **Visual Integrity**: The UI clearly labels the category and trust tier of every plugin output.
- **Safety**: Plugins do not have direct access to the database or file system by default. They receive standard EEG data dictionaries and should return JSON-serializable structures.

## 4. Local Development Flow

1. **Create the folder**: `plugins/local/my_plugin`.
2. **Define the manifest**: Point the `entrypoint` to your script.
3. **Write the code**: Implement the required contract method (e.g., `analyze`).
4. **Restart**: The NeuroVynx backend discovers enabled plugins on startup. Check the console logs for "Discovered plugin".
5. **Verify**: Open the dashboard and navigate to a session segment. Your plugin findings will appear in the "Plugin Insights" sidebar.

## 5. Deployment Checklist

- [ ] Does the manifest have a unique `plugin_id`?
- [ ] Is the entrypoint class a subclass of the appropriate plugin contract?
- [ ] Are all results JSON serializable (e.g., convert `np.float64` to `float`)?
- [ ] Does the plugin fail safely and return clear errors when execution fails?
- [ ] Does the plugin handle missing or noisy signal gracefully?

---
> [!IMPORTANT]
> NeuroVynx plugins are research tools. They are not intended for clinical diagnostic use. Developers should include appropriate caveats in their plugin descriptions.
