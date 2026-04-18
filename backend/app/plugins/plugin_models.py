from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum

class TrustTier(str, Enum):
    CORE_CERTIFIED = "core_certified"
    OFFICIAL_EXPERIMENTAL = "official_experimental"
    COMMUNITY_REVIEWED = "community_reviewed"
    UNVERIFIED_LOCAL = "unverified_local"

class PluginCategory(str, Enum):
    ANALYTICS = "analytics"
    VISUALIZATION = "visualization"
    IMPORTER = "importer"
    EXPORTER = "exporter"
    NORMATIVE = "normative"
    WORKFLOW = "workflow"

class PluginManifest(BaseModel):
    plugin_id: str
    name: str
    version: str
    author: str
    category: PluginCategory
    trust_tier: TrustTier
    permissions: List[str] = Field(default_factory=list)
    entrypoint: str
    plugin_api_version: str
    minimum_app_version: Optional[str] = None
    description: Optional[str] = None

class PluginStatus(str, Enum):
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    FAILED = "failed"
    INCOMPATIBLE = "incompatible"

class PluginInfo(BaseModel):
    manifest: PluginManifest
    status: PluginStatus
    enabled: bool
    path: str
    error_state: Optional[str] = None
    last_error: Optional[str] = None

class PluginOutput(BaseModel):
    plugin_id: str
    version: str
    trust_tier: TrustTier
    category: PluginCategory
    status: str = "success"
    result: Any
    error_message: Optional[str] = None
    hook_stage: Optional[str] = None
