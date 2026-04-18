from abc import ABC, abstractmethod
from typing import Any, Dict, List
import numpy as np
from .plugin_models import PluginManifest, TrustTier, PluginCategory

class PluginContract(ABC):
    """Base contract for all plugins."""
    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        pass

class AnalyticsPlugin(PluginContract):
    """Contract for custom analytics and feature extraction."""
    @abstractmethod
    def analyze(self, data_uv: np.ndarray, sfreq: float, channels: List[str]) -> Any:
        """
        Processes EEG data and returns a serializable result.
        data_uv: (n_channels, n_samples)
        """
        pass

class VisualizationPlugin(PluginContract):
    """Contract for custom UI data preparation."""
    @abstractmethod
    def render_payload(self, core_analysis_result: Dict[str, Any]) -> Any:
        """
        Takes core analysis result and returns a payload for the frontend template.
        """
        pass

class ImporterPlugin(PluginContract):
    """Contract for custom file format importers."""
    @abstractmethod
    def import_file(self, file_path: str) -> Dict[str, Any]:
        """
        Loads an external file format and returns a normalized NeuroVynx-compatible dict.
        """
        pass

class NormativePlugin(PluginContract):
    """Contract for external normative comparisons."""
    @abstractmethod
    def compare(self, qeeg_results: Dict[str, Any]) -> Any:
        """
        Compares results against external norms and returns comparison metrics.
        """
        pass

class WorkflowPlugin(PluginContract):
    """Contract for batch processing and automated workflows."""
    @abstractmethod
    def run_workflow(self, session_context: Dict[str, Any]) -> Any:
        """
        Executes a sequence of steps for a given session.
        """
        pass
