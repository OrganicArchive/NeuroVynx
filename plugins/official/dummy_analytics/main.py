from app.plugins.contracts import AnalyticsPlugin
from app.plugins.plugin_models import PluginManifest, TrustTier, PluginCategory
import numpy as np
from typing import List, Any

class DummyAnalyticsPlugin(AnalyticsPlugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            plugin_id="official.dummy_analytics",
            name="Dummy Analytics",
            version="1.0.0",
            author="NeuroVynx Core",
            category=PluginCategory.ANALYTICS,
            trust_tier=TrustTier.OFFICIAL_EXPERIMENTAL,
            permissions=["ui_render"],
            entrypoint="main.py",
            plugin_api_version="1",
            description="A dummy analytics plugin for testing Phase 19 hooks."
        )

    def analyze(self, data_uv: np.ndarray, sfreq: float, channels: List[str]) -> Any:
        return {
            "template": "key-value",
            "data": {
                "Mean Amplitude": float(np.mean(data_uv)),
                "Max Amplitude": float(np.max(data_uv)),
                "Channel Count": len(channels),
                "Sample Frequency": sfreq
            }
        }
