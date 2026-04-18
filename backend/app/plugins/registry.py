import json
import os
from typing import Dict, List, Optional
from .plugin_models import PluginInfo, PluginManifest, PluginStatus, TrustTier, PluginCategory

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        # Simple persistence for enabled status in a local JSON file if needed
        # For v1, we'll keep it in memory or simple file-backed dict
        self._enabled_cache_path = os.path.join(os.path.dirname(__file__), "registry_state.json")
        self._enabled_ids = self._load_enabled_state()

    def _load_enabled_state(self) -> List[str]:
        if os.path.exists(self._enabled_cache_path):
            try:
                with open(self._enabled_cache_path, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_enabled_state(self):
        try:
            with open(self._enabled_cache_path, "w") as f:
                json.dump(self._enabled_ids, f)
        except:
            pass

    def register_plugin(self, manifest: PluginManifest, path: str):
        plugin_id = manifest.plugin_id
        is_enabled = plugin_id in self._enabled_ids
        
        status = PluginStatus.LOADED
        if manifest.plugin_api_version != "1": # v1 hardcoded version check
            status = PluginStatus.INCOMPATIBLE

        self._plugins[plugin_id] = PluginInfo(
            manifest=manifest,
            status=status if is_enabled else PluginStatus.DISABLED,
            enabled=is_enabled,
            path=path
        )

    def get_enabled_plugins(self, category: Optional[PluginCategory] = None) -> List[PluginInfo]:
        results = [p for p in self._plugins.values() if p.enabled and p.status != PluginStatus.INCOMPATIBLE]
        if category:
            results = [p for p in results if p.manifest.category == category]
        # Sort by plugin_id for deterministic execution order
        results.sort(key=lambda p: p.manifest.plugin_id)
        return results

    def get_all_plugins(self) -> List[PluginInfo]:
        return list(self._plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        return self._plugins.get(plugin_id)

    def toggle_plugin(self, plugin_id: str, enabled: bool):
        if plugin_id in self._plugins:
            self._plugins[plugin_id].enabled = enabled
            if enabled:
                if plugin_id not in self._enabled_ids:
                    self._enabled_ids.append(plugin_id)
                # Re-verify compatibility before enabling
                if self._plugins[plugin_id].manifest.plugin_api_version == "1":
                    self._plugins[plugin_id].status = PluginStatus.ENABLED
                else:
                    self._plugins[plugin_id].status = PluginStatus.INCOMPATIBLE
            else:
                if plugin_id in self._enabled_ids:
                    self._enabled_ids.remove(plugin_id)
                self._plugins[plugin_id].status = PluginStatus.DISABLED
            
            self._save_enabled_state()

    def update_plugin_status(self, plugin_id: str, status: PluginStatus, error_msg: Optional[str] = None):
        if plugin_id in self._plugins:
            self._plugins[plugin_id].status = status
            if error_msg:
                self._plugins[plugin_id].last_error = error_msg
                self._plugins[plugin_id].error_state = "error"

    def validate_compatibility(self, plugin_id: str) -> bool:
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return False
        return plugin.manifest.plugin_api_version == "1"

# Singleton instance
registry = PluginRegistry()
