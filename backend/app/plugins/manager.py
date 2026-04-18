import logging
from typing import List, Dict, Any
import numpy as np
from .registry import registry
from .loader import instantiate_plugin
from .sandbox import execute_plugin_safely
from .plugin_models import PluginOutput, PluginCategory, PluginStatus
from .contracts import AnalyticsPlugin, VisualizationPlugin

logger = logging.getLogger("plugins.manager")

class PluginManager:
    def __init__(self):
        # Cache for instantiated plugin objects to avoid repeated loading
        self._instances: Dict[str, Any] = {}

    def _get_instance(self, plugin_id: str) -> Any:
        if plugin_id not in self._instances:
            instance = instantiate_plugin(plugin_id)
            if instance:
                self._instances[plugin_id] = instance
        return self._instances.get(plugin_id)

    def run_analytics_plugins(self, data_uv: np.ndarray, sfreq: float, channels: List[str]) -> List[PluginOutput]:
        """Runs all enabled analytics plugins at Hook Stage B."""
        results = []
        enabled_plugins = registry.get_enabled_plugins(category=PluginCategory.ANALYTICS)
        
        for p_info in enabled_plugins:
            instance = self._get_instance(p_info.manifest.plugin_id)
            if instance and isinstance(instance, AnalyticsPlugin):
                output = execute_plugin_safely(
                    plugin_id=p_info.manifest.plugin_id,
                    method=instance.analyze,
                    args=(data_uv, sfreq, channels),
                    hook_stage="post_features"
                )
                results.append(output)
            else:
                logger.warning(f"Plugin {p_info.manifest.plugin_id} enabled but instance not available or incorrect type")
        
        return results

    def run_visualization_plugins(self, core_analysis_result: Dict[str, Any]) -> List[PluginOutput]:
        """Runs all enabled visualization plugins at Hook Stage C."""
        results = []
        enabled_plugins = registry.get_enabled_plugins(category=PluginCategory.VISUALIZATION)
        
        for p_info in enabled_plugins:
            instance = self._get_instance(p_info.manifest.plugin_id)
            if instance and isinstance(instance, VisualizationPlugin):
                output = execute_plugin_safely(
                    plugin_id=p_info.manifest.plugin_id,
                    method=instance.render_payload,
                    args=(core_analysis_result,),
                    hook_stage="post_interpretation"
                )
                results.append(output)
        
        return results

# Singleton instance
manager = PluginManager()
