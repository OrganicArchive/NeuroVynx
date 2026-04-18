from app.plugins.contracts import VisualizationPlugin
from app.plugins.plugin_models import PluginManifest, TrustTier, PluginCategory
from typing import Dict, Any

class DummyVizPlugin(VisualizationPlugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            plugin_id="official.dummy_viz",
            name="Dummy Viz",
            version="1.0.0",
            author="NeuroVynx Core",
            category=PluginCategory.VISUALIZATION,
            trust_tier=TrustTier.CORE_CERTIFIED,
            permissions=["ui_render"],
            entrypoint="main.py",
            plugin_api_version="1",
            description="A dummy visualization plugin for testing Phase 19 hooks."
        )

    def render_payload(self, core_analysis_result: Dict[str, Any]) -> Any:
        return {
            "template": "table",
            "data": {
                "headers": ["Metric", "Value"],
                "rows": [
                    ["Core Status", core_analysis_result.get("preprocessing", {}).get("preprocessing_version", "unknown")],
                    ["Quality Score", core_analysis_result.get("quality", {}).get("eeg_quality_score", 0)]
                ]
            }
        }
