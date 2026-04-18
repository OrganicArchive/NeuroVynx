import os
import json
import importlib.util
import logging
from typing import Optional, List, Type
from .plugin_models import PluginManifest, TrustTier, PluginCategory
from .registry import registry
from .contracts import PluginContract

logger = logging.getLogger("plugins.loader")

def load_manifest(plugin_path: str) -> Optional[PluginManifest]:
    manifest_file = os.path.join(plugin_path, "manifest.json")
    if not os.path.exists(manifest_file):
        return None
    try:
        with open(manifest_file, "r") as f:
            data = json.load(f)
            return PluginManifest(**data)
    except Exception as e:
        logger.error(f"Failed to load manifest at {manifest_file}: {str(e)}")
        return None

def instantiate_plugin(plugin_id: str) -> Optional[PluginContract]:
    plugin_info = registry.get_plugin(plugin_id)
    if not plugin_info or not plugin_info.enabled:
        return None

    entrypoint_path = os.path.join(plugin_info.path, plugin_info.manifest.entrypoint)
    if not os.path.exists(entrypoint_path):
        logger.error(f"Entrypoint {entrypoint_path} not found for plugin {plugin_id}")
        return None

    try:
        spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", entrypoint_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Look for a class that implements PluginContract
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if (isinstance(attribute, type) and 
                issubclass(attribute, PluginContract) and 
                attribute is not PluginContract):
                # Found the class, instantiate it
                return attribute()
    except Exception as e:
        logger.error(f"Failed to instantiate plugin {plugin_id}: {str(e)}")
        registry.update_plugin_status(plugin_id, "failed", str(e))
        return None

    return None

def discover_plugins(base_dirs: List[str]):
    """Scans base directories for plugins and registers them."""
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
            continue

        for item in os.listdir(base_dir):
            plugin_path = os.path.join(base_dir, item)
            if os.path.isdir(plugin_path):
                manifest = load_manifest(plugin_path)
                if manifest:
                    # Additional check for trust tier based on directory
                    # This is a simple governance rule for v1
                    if "official" in base_dir and manifest.trust_tier not in [TrustTier.CORE_CERTIFIED, TrustTier.OFFICIAL_EXPERIMENTAL]:
                        logger.warning(f"Plugin {manifest.plugin_id} in 'official' dir has non-official trust tier {manifest.trust_tier}")
                    
                    registry.register_plugin(manifest, plugin_path)
                    logger.info(f"Discovered plugin: {manifest.name} ({manifest.plugin_id})")

def init_plugin_system():
    """Initializer to be called on app startup."""
    # Define standard plugin locations
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    official_plugins_dir = os.path.join(app_root, "plugins", "official")
    local_plugins_dir = os.path.join(app_root, "plugins", "local")

    discover_plugins([official_plugins_dir, local_plugins_dir])
