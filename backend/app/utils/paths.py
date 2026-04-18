import os
from app.core.config import settings

def ensure_valid_path(recorded_path: str) -> str:
    """
    Self-healing file path utility for machine portability.
    
    If the absolute path recorded in the DB no longer exists (e.g., project moved to a new PC),
    this utility attempts to locate the file within the current project's DATA_DIR
    by extracting the filename from the recorded path.
    """
    if os.path.exists(recorded_path):
        return recorded_path
        
    # PC-A to PC-B Migration Support
    filename = os.path.basename(recorded_path)
    current_pc_path = os.path.join(settings.DATA_DIR, filename)
    
    if os.path.exists(current_pc_path):
        return current_pc_path
        
    # Fallback to the original path if both fail (will trigger 404 in caller)
    return recorded_path
