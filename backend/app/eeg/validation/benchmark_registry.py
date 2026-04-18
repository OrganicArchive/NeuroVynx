"""
NeuroVynx: Benchmark Case Registry
===================================
Defines the canonical suite of validation cases used to certify research-readiness.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class BenchmarkCase(BaseModel):
    """Formal definition of a validation scenario."""
    benchmark_id: str
    title: str
    scenario_group: str # e.g., "physiological", "artifact", "temporal"
    source_type: str # synthetic, curated, real
    purpose: str
    
    # Input Data
    input_reference: str # Path to EDF or recipe name
    optional_comparison_reference: Optional[str] = None
    quality_override: Optional[Dict[str, Any]] = None
    
    # Behavioral Expectations (Semantic)
    expected_behaviors: List[str] = Field(default_factory=list)
    expected_non_behaviors: List[str] = Field(default_factory=list)
    
    # Structural Expectations (Gated Tiers)
    expected_confidence_band: List[float] = Field([0.0, 1.0], min_length=2, max_length=2)
    expected_priority_profile: Dict[str, str] = Field(default_factory=dict) # type -> priority
    expected_render_mode: Optional[str] = None
    expected_temporal_classification: Optional[Dict[str, str]] = None
    expected_trend_status: Optional[str] = None
    
    notes: Optional[str] = None

# INITIAL CORE BENCHMARK PACK
CORE_BENCHMARKS: List[BenchmarkCase] = [
    BenchmarkCase(
        benchmark_id="clean_posterior_alpha_resting",
        title="Clean Eyes-Closed Resting Alpha",
        scenario_group="physiological",
        source_type="curated",
        purpose="Verify preservation of strong, normal physiological patterns.",
        input_reference="case_a_clean.edf",
        expected_behaviors=["alpha_dominance", "strong_supported_wording"],
        expected_non_behaviors=["contradiction_detected", "artifact_suppression"],
        expected_confidence_band=[0.8, 1.0],
        expected_priority_profile={"posterior_alpha": "primary"},
        expected_render_mode="full_topography"
    ),
    BenchmarkCase(
        benchmark_id="emg_confounded_frontal_beta",
        title="EMG-Confounded Frontal Beta",
        scenario_group="artifact",
        source_type="synthetic",
        purpose="Verify that muscle noise correctly penalizes beta elevations.",
        input_reference="case_c_line_noise.edf",
        quality_override={"artifact_flags": {"muscle_noise": True}},
        expected_behaviors=["contradiction_detected", "confidence_downgrade"],
        expected_non_behaviors=["strong_supported_beta"],
        expected_confidence_band=[0.3, 0.7]
    ),
    BenchmarkCase(
        benchmark_id="sparse_support_topography",
        title="Sparse Channel Topography Gating",
        scenario_group="spatial",
        source_type="synthetic",
        purpose="Verify that isolated sensor deviations are suppressed.",
        input_reference="case_d_unstable.edf",
        expected_behaviors=["spatial_masking_applied", "technical_only_visibility"],
        expected_non_behaviors=["regional_slowing_pattern"],
        expected_confidence_band=[0.2, 0.5],
        expected_render_mode="limited_render"
    ),
    BenchmarkCase(
        benchmark_id="transient_noise_burst",
        title="Transient Artifact Burst",
        scenario_group="temporal",
        source_type="synthetic",
        purpose="Verify that brief events are not classified as sustained.",
        input_reference="case_b_blinks.edf",
        expected_behaviors=["transient_classification", "brief_hedging"],
        expected_non_behaviors=["sustained_classification", "stable_pattern"],
        expected_confidence_band=[0.3, 0.6],
        expected_temporal_classification={"blink": "transient"}
    ),
    BenchmarkCase(
        benchmark_id="stable_temporal_alpha",
        title="Stable Temporal Alpha Organization",
        scenario_group="temporal",
        source_type="curated",
        purpose="Verify that persistent neural features are elevated to stable.",
        input_reference="case_f_alpha_reduction.edf",
        expected_behaviors=["stable_classification", "strong_supported_wording"],
        expected_confidence_band=[0.75, 0.95]
    ),
    BenchmarkCase(
        benchmark_id="mismatched_session_trend_block",
        title="Mismatched Session Trend Gating",
        scenario_group="longitudinal",
        source_type="synthetic",
        purpose="Verify that trend analysis is blocked when files are incompatible.",
        input_reference="case_a_clean.edf",
        optional_comparison_reference="case_d_unstable.edf", # Very different quality
        expected_behaviors=["trend_block_detected", "ineligibility_summary"],
        expected_non_behaviors=["trend_calculation_allowed"],
        expected_trend_status="ineligible"
    ),
    BenchmarkCase(
        benchmark_id="poor_quality_global_suppression",
        title="Poor Quality Global Suppression",
        scenario_group="artifact",
        source_type="curated",
        purpose="Verify that very low SNR suppresses all neural claims.",
        input_reference="case_d_unstable.edf",
        expected_behaviors=["global_confidence_fail", "blocked_priority"],
        expected_non_behaviors=["any_primary_finding"],
        expected_confidence_band=[0.0, 0.4],
        expected_priority_profile={"all": "blocked"}
    )
]

def get_benchmark(benchmark_id: str) -> Optional[BenchmarkCase]:
    """Retrieves a benchmark case by ID."""
    for b in CORE_BENCHMARKS:
        if b.benchmark_id == benchmark_id:
            return b
    return None

def get_suite(group: Optional[str] = None) -> List[BenchmarkCase]:
    """Returns a subset or all benchmark cases."""
    if not group:
        return CORE_BENCHMARKS
    return [b for b in CORE_BENCHMARKS if b.scenario_group == group]
