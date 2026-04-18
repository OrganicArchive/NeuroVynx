from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..plugins.registry import registry
from ..plugins.plugin_models import PluginInfo, PluginStatus

router = APIRouter()

@router.get("", response_model=List[PluginInfo])
def list_plugins():
    return registry.get_all_plugins()

@router.get("/{plugin_id}", response_model=PluginInfo)
def get_plugin_details(plugin_id: str):
    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin

@router.post("/{plugin_id}/toggle")
def toggle_plugin(plugin_id: str, enabled: bool):
    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    registry.toggle_plugin(plugin_id, enabled)
    return {"status": "success", "enabled": enabled}

@router.get("/{plugin_id}/status")
def get_plugin_status(plugin_id: str):
    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {
        "status": plugin.status,
        "last_error": plugin.last_error,
        "error_state": plugin.error_state
    }
