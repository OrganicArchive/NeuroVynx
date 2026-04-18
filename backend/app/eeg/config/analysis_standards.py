"""
NeuroVynx: Canonical Analysis Standards
========================================

This module serves as the single source of truth for all analytical 
assumptions, band definitions, and coordinate mappings across the platform.

All analytic modules must import constants and helpers from here to ensure 
cross-layer consistency.
"""

import re

# 1. CANONICAL BANDS
# --------------------------------------------------------------------------
# Strictly follow the clinical standard for band ranges.
# Logic: [low, high) - includes low, excludes high.
CANONICAL_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0)
}

# 2. SPECTRAL NORMALIZATION STANDARDS
# --------------------------------------------------------------------------
# Use 0.5 - 30.0 Hz as the standard denominator for all relative power metrics.
TOTAL_POWER_RANGE = (0.5, 30.0)

# Guard against division by zero
EPSILON = 1e-12

# 2.1 HARDENING THRESHOLDS (Phase 2)
# --------------------------------------------------------------------------
# Minimum signal quality (0-100) required to use a channel for normative comparison
MIN_QUALITY_FOR_NORM = 60
# Minimum interpretive confidence (0.0 - 1.0) required for regional claims
MIN_INTERPRETATION_CONFIDENCE = 0.5
# Minimum distinct electrodes supporting a regional finding
MIN_REGIONAL_SUPPORT_COUNT = 2
# Minimum total clean electrodes for any topographical map
MIN_TOPO_CHANNELS = 6
# Standard radius for support influence in topomaps (normalized units)
TOPO_SUPPORT_RADIUS = 0.4
# Threshold for geometry spread score (0.0 to 1.0)
MIN_GEOMETRY_SCORE_FOR_FULL_RENDER = 0.7

# 2.2 TEMPORAL & TREND HARDENING (Phase 3)
# --------------------------------------------------------------------------
# Minimum windows required to make ANY temporal claim
MIN_WINDOWS_FOR_TEMPORAL_CLAIM = 3
# Minimum valid windows for a claim to appear in the primary summary
MIN_VALID_WINDOWS_FOR_SUMMARY_CLAIM = 4
# Minimum consecutive windows for a finding to be called 'sustained'
MIN_CONSECUTIVE_WINDOWS_FOR_SUSTAINED = 2
# Ratio of valid windows where finding is present for 'sustained' (>= 70%)
PERSISTENCE_RATIO_SUSTAINED = 0.7
# Ratio for 'recurring' (>= 40%)
PERSISTENCE_RATIO_RECURRING = 0.4
# Threshold for trend confidence (0.0 to 1.0)
TREND_CONFIDENCE_MIN = 0.6

# Session Comparability Thresholds
# Minimum ratio of common channels between sessions to allow trend calculation
MIN_SESSION_OVERLAP_RATIO_FOR_TREND = 0.75
# Minimum ratio for 'strong' comparability
STRONG_OVERLAP_THRESHOLD = 0.90
# Maximum allowed change in global quality between sessions (%)
MAX_ALLOWED_QUALITY_DELTA_SESSIONS = 50.0 
# Required preprocessing version compatibility score
MIN_PREPROCESSING_COMPATIBILITY_SCORE = 0.8

# Normative Significance Tiers
Z_SIGNIFICANCE_MILD = 1.65     # ~95th percentile
Z_SIGNIFICANCE_MODERATE = 2.0  # Common clinical threshold
Z_SIGNIFICANCE_STRONG = 2.58   # ~99th percentile

# Topography Rendering Modes
RENDER_MODES = {
    "FULL": "full_render",           # Clean, high-density support
    "CAUTIOUS": "cautious_render",   # Adequate support, but lower confidence
    "LIMITED": "limited_render",     # Sparse/Asymmetric support (partial masking)
    "SUPPRESSED": "suppressed_render" # Insufficient support for spatial claims
}

# 3. REGIONAL MAPPING STANDARDS
# --------------------------------------------------------------------------
REGION_MAPPING = {
    "Frontal": ["FP1", "FP2", "F3", "F4", "F7", "F8", "FZ", "FPZ"],
    "Central": ["C3", "C4", "CZ"],
    "Parietal": ["P3", "P4", "PZ"],
    "Occipital": ["O1", "O2", "OZ"],
    "Temporal": ["T3", "T7", "T4", "T8", "T5", "P7", "T6", "P8"]
}

CHANNEL_ALIASES = {
    "T3": "T7", "T7": "T3",
    "T4": "T8", "T8": "T4",
    "T5": "P7", "P7": "T5",
    "T6": "P8", "P8": "T6"
}

ASYMMETRY_PAIRS = [
    ("F3", "F4"),
    ("C3", "C4"),
    ("P3", "P4"),
    ("O1", "O2")
]

# 4. ELECTRODE COORDINATES (Scaled to -1.1 to 1.1)
# --------------------------------------------------------------------------
# Mapping logic: Anterior (Top) is +Y, Posterior (Bottom) is -Y.
# Left is -X, Right is +X.
ELECTRODE_MAP = {
    "FP1": (-0.31, 0.95),  "FP2": (0.31, 0.95),   "FPZ": (0, 1.05),
    "F7":  (-0.81, 0.59),  "F3":  (-0.55, 0.67),  "FZ": (0, 0.71),   "F4": (0.55, 0.67),  "F8": (0.81, 0.59),
    "T3":  (-0.95, 0),     "C3":  (-0.71, 0),     "CZ": (0, 0),      "C4": (0.71, 0),     "T4": (0.95, 0),
    "T5":  (-0.81, -0.59), "P3":  (-0.55, -0.67), "PZ": (0, -0.71),  "P4": (0.55, -0.67), "T6": (0.81, -0.59),
    "O1":  (-0.31, -0.95), "O2":  (0.31, -0.95),  "OZ": (0, -0.95),
    
    # 10-10 Extended Positions (Optional Support)
    "T7":  (-0.95, 0),     "T8":  (0.95, 0),
    "P7":  (-0.81, -0.59), "P8":  (0.81, -0.59)
}

# 5. CHANNEL NORMALIZATION
# --------------------------------------------------------------------------
def clean_name(name: str) -> str:
    """
    Canonical channel name normalization.
    Ensures that variations like 'Fp1', 'EEG FP1', 'O1-REF' map 
    to the consistent library standard (FP1, O1, etc).
    """
    if not name: return "UNKNOWN"
    
    # Standard cleanup
    s = name.upper().strip()
    s = s.replace('EEG', '').strip()
    s = s.replace('-REF', '').replace('-LE', '').replace('-AV', '')
    s = s.strip('.')
    
    # Handle specific common regex variants
    s = re.sub(r'[^A-Z0-9]', '', s) # Strip symbols except letters/numbers
    
    # Special Alias Mapping (e.g., Fp1 -> FP1)
    if s == "FP1": return "FP1"
    if s == "FP2": return "FP2"
    if s == "FPZ": return "FPZ"
    
    return s

def get_region_for_channel(channel_name: str) -> str:
    """Identifies region based on normalized label and aliases."""
    normalized = clean_name(channel_name)
    for region, channels in REGION_MAPPING.items():
        if normalized in channels:
            return region
        # Check aliases
        if normalized in CHANNEL_ALIASES:
            if CHANNEL_ALIASES[normalized] in channels:
                return region
    return "Unknown"

