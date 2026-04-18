import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from threading import Lock

# Singleton access to the cache
_CACHE_LOCK = Lock()
_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}  # Key: file_path_hash
_SPECTRAL_CACHE: Dict[str, Dict[str, Any]] = {}  # Key: window_hash (includes file+range+params)
_INTERPRETATION_CACHE: Dict[str, Dict[str, Any]] = {} # Key: interp_hash (includes spectral+standards)

# VERSION CONSTANTS (Sync with models.py)
APP_VERSION = "0.9.0"
PIPELINE_VERSION = "phase_5_2"
STANDARDS_VERSION = "2026.04"

def generate_file_hash(file_path: str) -> str:
    """Stable identifier for a file based on its path and metadata."""
    # In production, we'd use os.path.getmtime to detect changes
    content = f"{file_path}_{APP_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()

def generate_window_key(
    file_path: str, 
    start: float, 
    duration: float, 
    preprocessing: Dict[str, Any]
) -> str:
    """Generates a cache key for a specific analysis window."""
    prep_str = json.dumps(preprocessing, sort_keys=True)
    content = f"{file_path}_{start}_{duration}_{prep_str}_{PIPELINE_VERSION}_{STANDARDS_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()

def get_cached_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """Retrieves Level 1 Metadata Cache (File Header Info)."""
    key = generate_file_hash(file_path)
    with _CACHE_LOCK:
        if key in _METADATA_CACHE:
            print(f"[CACHE HIT] Level 1: Metadata for {os.path.basename(file_path)}")
            return _METADATA_CACHE[key]
    return None

def set_cached_metadata(file_path: str, data: Dict[str, Any]):
    """Stores Level 1 Metadata Cache."""
    key = generate_file_hash(file_path)
    with _CACHE_LOCK:
        _METADATA_CACHE[key] = data

def get_cached_spectral(
    file_path: str, 
    start: float, 
    duration: float, 
    preprocessing: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Retrieves Level 3 Spectral Feature Cache (PSD, Band Powers)."""
    key = generate_window_key(file_path, start, duration, preprocessing)
    with _CACHE_LOCK:
        if key in _SPECTRAL_CACHE:
            print(f"[CACHE HIT] Level 3: Spectral Features at {start}s")
            return _SPECTRAL_CACHE[key]
    return None

def set_cached_spectral(
    file_path: str, 
    start: float, 
    duration: float, 
    preprocessing: Dict[str, Any], 
    data: Dict[str, Any]
):
    """Stores Level 3 Spectral Feature Cache."""
    key = generate_window_key(file_path, start, duration, preprocessing)
    with _CACHE_LOCK:
        _SPECTRAL_CACHE[key] = data

def clear_cache():
    """Wipes all in-memory caches. Used during testing or version change."""
    with _CACHE_LOCK:
        _METADATA_CACHE.clear()
        _SPECTRAL_CACHE.clear()
        _INTERPRETATION_CACHE.clear()
    print("[CACHE] All layers flushed.")

import os # Required for basename
