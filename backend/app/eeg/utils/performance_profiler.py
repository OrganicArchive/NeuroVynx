import time
import functools
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Global registry for performance metrics during a session
_SESSIONS: Dict[str, Dict[str, Any]] = {}

def start_profiling_session(session_id: str):
    """Initializes a new recording for performance tracking."""
    _SESSIONS[session_id] = {
        "start_time": datetime.now().isoformat(),
        "total_ms": 0.0,
        "checkpoints": {},
        "hotspots": []
    }

def get_session_report(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the aggregated performance data for a session."""
    return _SESSIONS.get(session_id)

def profile_block(name: str):
    """
    Context manager for manual profiling of specific logic blocks.
    Usage:
        with profile_block("fft_computation"):
            # logic here
    """
    class ProfileContext:
        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = (time.perf_counter() - self.start) * 1000
            # For simplicity in this iteration, we print to stdout
            # In Phase 14 full integration, we will route this to _SESSIONS
            print(f"[PROFILE] {name}: {elapsed:.2f}ms")

    return ProfileContext()

def profile_function(name: Optional[str] = None):
    """
    Decorator for automated timing of function execution.
    Usage:
        @profile_function("qEEG Pipeline")
        def run_analysis(...):
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            display_name = name or func.__name__
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            print(f"[PROFILE] {display_name}: {elapsed:.2f}ms")
            return result
        return wrapper
    return decorator

def save_baseline(filename: str, data: Dict[str, Any]):
    """Saves profiling data to a JSON baseline file."""
    base_path = "backend/docs/validation/performance/"
    os.makedirs(base_path, exist_ok=True)
    with open(os.path.join(base_path, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
