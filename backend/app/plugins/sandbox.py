import logging
from typing import Any, Callable, Optional, Dict
from .plugin_models import PluginOutput, PluginStatus, PluginCategory, TrustTier
from .registry import registry

logger = logging.getLogger("plugins.sandbox")

def execute_plugin_safely(
    plugin_id: str,
    method: Callable,
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
    hook_stage: Optional[str] = None
) -> PluginOutput:
    """
    Wraps plugin execution in a try-except block to prevent crashes.
    Returns a PluginOutput object indicating success or failure.
    """
    plugin_info = registry.get_plugin(plugin_id)
    if not plugin_info:
        return PluginOutput(
            plugin_id=plugin_id,
            version="unknown",
            trust_tier=TrustTier.UNVERIFIED_LOCAL,
            category=PluginCategory.ANALYTICS,
            status="failed",
            result=None,
            error_message="Plugin not found in registry"
        )

    manifest = plugin_info.manifest
    args = args or ()
    kwargs = kwargs or {}

    try:
        result = method(*args, **kwargs)
        return PluginOutput(
            plugin_id=plugin_id,
            version=manifest.version,
            trust_tier=manifest.trust_tier,
            category=manifest.category,
            status="success",
            result=result,
            hook_stage=hook_stage
        )
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Plugin {plugin_id} failed during execution: {error_msg}")
        
        # Update registry with error status for UI visibility
        registry.update_plugin_status(plugin_id, PluginStatus.FAILED, error_msg)
        
        return PluginOutput(
            plugin_id=plugin_id,
            version=manifest.version,
            trust_tier=manifest.trust_tier,
            category=manifest.category,
            status="failed",
            result=None,
            error_message=error_msg,
            hook_stage=hook_stage
        )
