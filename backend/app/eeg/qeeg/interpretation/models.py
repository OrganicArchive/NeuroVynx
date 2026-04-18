from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class InterpretationMetadata(BaseModel):
    """Metadata for reproducibility and readiness tracking."""
    app_version: str = "0.9.0"
    pipeline_version: str = "phase_5_2"
    standards_version: str = "2026.04"
    benchmark_suite_version: str = "core7_v1"
    summary_version: str = "hierarchy_v1"
    readiness_status: str = "INTERNAL_RESEARCH_READY"
    build_date: str = "2026-04-17"

class ConfidenceResult(BaseModel):
    """Represents the multi-layered confidence assessment of the interpretation."""
    global_score: float = Field(..., description="Overall confidence score (0.0 to 1.0)")
    global_level: str = Field(..., description="Confidence level (high, moderate, low)")
    per_channel: Dict[str, float] = Field(default_factory=dict, description="Confidence per channel")
    per_region: Dict[str, float] = Field(default_factory=dict, description="Confidence per region")
    per_metric: Dict[str, float] = Field(default_factory=dict, description="Confidence per qEEG metric")
    reasons: List[str] = Field(default_factory=list, description="Reasons for confidence reduction")
    trend_traceability: Optional[TrendTraceability] = Field(None, description="Metadata regarding longitudinal comparisons")

class FindingTemporalMetadata(BaseModel):
    """Temporal support details for a specific finding."""
    present_in_window_count: int
    eligible_window_count: int
    persistence_ratio: float = Field(..., ge=0.0, le=1.0)
    consecutive_support_max: int
    temporal_classification: str = Field(..., description="transient, recurring, sustained, stable")
    temporal_confidence_score: float = Field(..., ge=0.0, le=1.0)
    summary_visibility: str = Field(..., description="primary, secondary")

class TrendTraceability(BaseModel):
    """Metadata regarding longitudinal comparisons."""
    comparison_session_id: Optional[str] = None
    comparable_channel_count: int
    overlap_ratio: float = Field(..., ge=0.0, le=1.0)
    preprocessing_compatible: bool
    trend_available: bool
    trend_comparable: bool
    trend_interpretation_eligible: bool
    change_classification: str = Field(..., description="no reliable change, possible, probable, strong stable change")
    change_confidence_score: float = Field(..., ge=0.0, le=1.0)
    ineligibility_reason: Optional[str] = None

class FindingEvidenceTrace(BaseModel):
    """Deep reasoning trace for a finding, capturing support and weakening factors."""
    supporting_evidence: List[str] = Field(default_factory=list)
    weakening_factors: List[str] = Field(default_factory=list)
    penalties: List[str] = Field(default_factory=list)
    final_reasoning_summary: Optional[str] = None

class FindingSuppressionInfo(BaseModel):
    """Detailed reasoning for withholding a finding from the final narrative."""
    is_suppressed: bool = False
    priority: str = Field("primary", description="primary, secondary_cautious, technical_only, blocked")
    reasons: List[str] = Field(default_factory=list)

class ContradictionResult(BaseModel):
    """Represents a detected conflict between findings or patterns."""
    type: str = Field(..., description="e.g., artifact_vs_neural")
    affected_finding: str
    action_taken: str = Field(..., description="downgrade, reduce_confidence, suppress")
    explanation: str

class FindingResult(BaseModel):
    """Represents a single deterministic deviation or candidate finding."""
    finding_name: str = Field(..., description="Unique slug for the finding type")
    type: str = Field(..., description="Finding category (e.g., band_power_abnormality)")
    metric: str = Field(..., description="Metric being evaluated")
    band: Optional[str] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    direction: str = Field(..., description="elevated, reduced")
    severity: str = Field(..., description="minimal, mild, moderate, marked")
    z_score: Optional[float] = None
    
    # Phase 4: Core Trust & Intelligence Fields
    detected: bool = True
    eligible: bool = True
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    raw_support_components: Dict[str, float] = Field(default_factory=dict)
    
    priority: str = Field("primary", description="primary, secondary_cautious, technical_only, blocked")
    language_level: str = Field("moderate_supported", description="strong_supported, moderate_supported, cautious, brief")
    
    evidence_trace: FindingEvidenceTrace = Field(default_factory=FindingEvidenceTrace)
    suppression_info: FindingSuppressionInfo = Field(default_factory=FindingSuppressionInfo)
    contradictions: List[ContradictionResult] = Field(default_factory=list)
    penalties_applied: List[Dict[str, Any]] = Field(default_factory=list)
    
    summary_text: Optional[str] = None
    explanation: str = Field(..., description="Legacy natural language explanation")
    weak_finding: bool = False
    temporal_metadata: Optional[FindingTemporalMetadata] = None

class PatternResult(BaseModel):
    """Represents a higher-order synthesis of multiple findings into a research pattern."""
    type: str = Field(..., description="Pattern class (e.g., focal_slowing)")
    label: str = Field(..., description="Display label for the pattern")
    regions: List[str] = Field(default_factory=list)
    bands: List[str] = Field(default_factory=list)
    supporting_findings: List[str] = Field(default_factory=list)
    
    detected: bool = True
    eligible: bool = True
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    priority: str = Field("primary")
    language_level: str = Field("moderate_supported")
    
    suppressed_due_to_artifact: bool = False
    suppression_info: FindingSuppressionInfo = Field(default_factory=FindingSuppressionInfo)
    evidence_trace: FindingEvidenceTrace = Field(default_factory=FindingEvidenceTrace)
    
    explanation: str = Field(..., description="Detailed explanation of the pattern")
    temporal_classification: Optional[str] = Field(None, description="transient, recurring, sustained, stable")

class InterpretationSummary(BaseModel):
    """Structured, layered summaries of the overall interpretation."""
    primary_narrative: str = Field(..., description="High-level interpretive headline")
    primary_points: List[str] = Field(default_factory=list, description="Top 2-5 concise high-value conclusions")
    
    secondary_narrative: Optional[str] = None
    secondary_points: List[str] = Field(default_factory=list, description="Narrower or lower-confidence findings")
    
    technical_note: str = Field(..., description="Summary of withheld or technical-only data")
    technical_items_count: int = 0
    suppressed_items_count: int = 0
    
    confidence_banner: Optional[str] = None
    summary_version: str = "1.1" # Tracks hierarchical engine version
    behavior_flags: List[str] = Field(default_factory=list, description="Machine-readable validation markers")
    
    # Legacy fields for backward compatibility during transition
    short: str = ""
    detailed: str = ""
    bullets: List[str] = Field(default_factory=list)
    technical_details: Dict[str, Any] = Field(default_factory=dict)

class AdvancedPatternResult(BaseModel):
    """Represents a richer, grouped qEEG pattern with temporal and spatial synthesis."""
    type: str = Field(..., description="Pattern identifier (e.g., regional_slowing)")
    label: str = Field(..., description="Human-readable label")
    family: str = Field(..., description="Pattern family (e.g., slowing, alpha_organization)")
    bands: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    supporting_findings: List[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str = Field(..., description="high, moderate, low")
    explanation: str = Field(..., description="Natural language reasoning")
    composite_of: Optional[List[str]] = Field(None, description="List of component pattern IDs if this is a composite")

class TemporalPatternResult(BaseModel):
    """Classification of how a pattern behaves over time across the recording."""
    pattern_label: str = Field(..., description="Label of the underlying pattern")
    temporal_classification: str = Field(..., description="PERSISTENT, INTERMITTENT, TRANSIENT, EVOLVING, ARTIFACT-LINKED")
    windows_present: int
    windows_total: int
    persistence_ratio: float = Field(..., ge=0.0, le=1.0)
    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str = Field(..., description="Overall confidence in this temporal classification")
    artifact_overlap_ratio: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., description="Reasoning for the temporal classification")

class WindowInterpretationSnapshot(BaseModel):
    """A point-in-time snapshot of a single window's interpretive state."""
    window_index: int
    start_time: float
    end_time: float
    findings: List[FindingResult]
    patterns: List[PatternResult]
    confidence: ConfidenceResult
    artifact_flags: List[str] = Field(default_factory=list)

class TemporalSummary(BaseModel):
    """Summaries focused on recording-level clinical trends."""
    short: str
    detailed: str
    bullets: List[str] = Field(default_factory=list)

class RecordingInterpretationResult(BaseModel):
    """The unified payload representing the entire recording's interpretive state."""
    sampled_windows: List[int]
    skipped_windows: List[Dict[str, Any]] = Field(default_factory=list, description="Windows that were too noisy to sample")
    window_snapshots: List[WindowInterpretationSnapshot]
    advanced_patterns: List[AdvancedPatternResult] = Field(default_factory=list)
    temporal_patterns: List[TemporalPatternResult] = Field(default_factory=list)
    temporal_summary: TemporalSummary
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    overall_confidence_level: str = Field(..., description="Normalized confidence across sampled windows")
    caveats: List[str] = Field(default_factory=list)

class MLArtifactPrediction(BaseModel):
    """Secondary ML suggestion for signal contaminants."""
    label: str
    probability: float
    confidence_band: str # high, moderate, low
    drivers: List[str] = Field(default_factory=list)
    advisory_status: str = "secondary_signal"
    disagreement_with_heiristics: bool = False

class ClusterMembership(BaseModel):
    """Unsupervised pattern similarity discovery."""
    cluster_id: str
    membership_strength: float
    description: str
    top_features: List[str] = Field(default_factory=list)
    similar_case_ids: List[str] = Field(default_factory=list)
    advisory_status: str = "exploratory"

class AnomalyAlert(BaseModel):
    """Alert for unusual spectral or temporal recordings."""
    target_id: str
    anomaly_score: float
    anomaly_band: str # high, moderate, low
    likely_drivers: List[str] = Field(default_factory=list)
    advisory_status: str = "review_recommended"

class AdvisoryMLSection(BaseModel):
    """Unified container for all secondary ML-assisted signals."""
    artifact_predictions: List[MLArtifactPrediction] = Field(default_factory=list)
    cluster_membership: Optional[ClusterMembership] = None
    anomaly_alerts: List[AnomalyAlert] = Field(default_factory=list)
    model_version: str = "1.0.0"
    research_mode_active: bool = False


class InterpretationResult(BaseModel):
    """The unified payload for the NeuroVynx Interpretive Intelligence Layer."""
    confidence: ConfidenceResult
    findings: List[FindingResult]
    patterns: List[PatternResult]
    top_patterns: List[str] = Field(default_factory=list, description="Priority labels for UI tags")
    summary: InterpretationSummary
    behavior_flags: List[str] = Field(default_factory=list, description="Overall session-level behavior markers")
    trend_traceability: Optional[TrendTraceability] = None
    advisory_ml: Optional[AdvisoryMLSection] = None
    metadata: InterpretationMetadata = Field(default_factory=InterpretationMetadata)

class ValidationLayerScore(BaseModel):
    """Score for a specific validation layer (e.g., Numerical, Spatial)."""
    score: float = Field(..., ge=0.0, le=1.0)
    status: str = Field(..., description="pass, pass_with_warnings, fail_minor, fail_critical")
    details: List[str] = Field(default_factory=list)

class ValidationCaseResult(BaseModel):
    """The outcome of a single benchmark case run."""
    benchmark_id: str
    pass_overall: bool
    status: str
    layer_scores: Dict[str, ValidationLayerScore] = Field(default_factory=dict)
    reproducibility_check: bool = True
    critical_failures: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0

class ValidationSuiteResult(BaseModel):
    """The aggregate outcome of a benchmark suite execution."""
    suite_id: str
    timestamp: str
    version_metadata: Dict[str, str]
    total_cases: int
    passed_count: int
    failed_count: int
    overall_pass_rate: float
    results: List[ValidationCaseResult] = Field(default_factory=list)
    readiness_recommendation: str = "not_ready"
