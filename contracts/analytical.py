"""
Analytical Input Contracts for Vigil-X Workstream Integration.

These Pydantic models define the stable contract boundaries between the external
analytical workstreams (ML & Risk Intelligence, Network Intelligence, Detection)
and the Vigil-X SQLite database / FastAPI backend.

The backend validates external inputs through these models before persistence.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ExternalSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── A & B: Alerts & Evidence Contracts ───────────────────────────────

class EvidenceInput(BaseModel):
    """Granular evidence item supporting a detection alert."""
    evidence_id: str = Field(..., min_length=1, description="Unique evidence ID (e.g., E-R01-abc-001)")
    rule_id: str = Field(..., pattern=r"^R(?:0[1-9]|10)$", description="Rule identifier (R01-R10)")
    rule_version: str = Field(default="1.0.0")
    claim_ids: List[str] = Field(default_factory=list, description="Associated claim IDs")
    fields_matched: List[str] = Field(default_factory=list, description="Fields involved in match")
    plain_text: str = Field(..., min_length=1, description="Human-readable evidence statement")
    est_overpay: float = Field(default=0.0, ge=0.0, description="Estimated dollar overpayment")
    severity: ExternalSeverity = Field(default=ExternalSeverity.MEDIUM)
    fp_notes: Optional[str] = Field(default=None, description="Known false positive considerations")


class AlertInput(BaseModel):
    """Detection alert emitted by R01-R10 or behavioral models."""
    alert_id: str = Field(..., min_length=1, description="Unique alert ID (e.g., A-R01-abc)")
    rule_id: str = Field(..., pattern=r"^R(?:0[1-9]|10)$", description="Rule identifier")
    rule_version: str = Field(default="1.0.0")
    entity_type: str = Field(default="provider", description="'provider', 'member', or 'facility'")
    entity_id: str = Field(..., min_length=1, description="Identifier of focal flagged entity")
    claim_ids: List[str] = Field(default_factory=list, description="Flagged claim IDs")
    severity: ExternalSeverity = Field(default=ExternalSeverity.MEDIUM)
    est_dollars: float = Field(default=0.0, ge=0.0, description="Estimated dollars at risk")
    evidence: List[EvidenceInput] = Field(default_factory=list, description="Supporting evidence items")
    fp_notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ── C: Claim ML Scores ──────────────────────────────────────────────

class ClaimMLScoreInput(BaseModel):
    """Claim-level supervised or unsupervised anomaly score."""
    claim_id: str = Field(..., min_length=1)
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Normalized anomaly score [0.0, 1.0]")
    ml_prediction: Optional[str] = Field(default=None, description="Prediction class or label")
    model_version: str = Field(default="1.0.0", description="Model training run / version string")


# ── D: Provider Anomaly Scores ──────────────────────────────────────

class ProviderAnomalyScoreInput(BaseModel):
    """Provider-level Isolation Forest or outlier score."""
    provider_id: str = Field(..., min_length=1)
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Outlier score [0.0, 1.0]")
    feature_contributions: Dict[str, float] = Field(
        default_factory=dict, description="SHAP or feature attribution values"
    )


# ── E: Network Scores & Features ────────────────────────────────────

class NetworkScoreInput(BaseModel):
    """Precomputed graph community and ring risk features."""
    network_id: str = Field(..., min_length=1, description="Unique network ID (e.g., NET-001)")
    community_id: int = Field(..., ge=0, description="Louvain / cluster partition ID")
    n_providers: int = Field(..., ge=1, description="Number of providers in network")
    hub_provider_id: str = Field(..., min_length=1, description="Central hub provider ID")
    hard_link_score: float = Field(default=0.0, ge=0.0, le=1.0)
    referral_score: float = Field(default=0.0, ge=0.0, le=1.0)
    concentration_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ownership_score: float = Field(default=0.0, ge=0.0, le=1.0)
    suspicious_claims: int = Field(default=0, ge=0)
    total_claims: int = Field(default=0, ge=0)
    total_exposure: float = Field(default=0.0, ge=0.0)
    triggered_rules: str = Field(default="", description="Comma-separated rule IDs")
    hub_centrality: float = Field(default=0.0, ge=0.0, le=1.0)
    documented_group: int = Field(default=0, ge=0, le=1)
    network_feature_version: str = Field(default="1.0.0")


# ── F: Future-Risk Scores ───────────────────────────────────────────

class FutureRiskScoreInput(BaseModel):
    """Forward-looking 30/60/90-day velocity risk projection."""
    entity_type: str = Field(default="provider")
    entity_id: str = Field(..., min_length=1)
    horizon_days: int = Field(default=30, ge=1, le=365)
    velocity_score: float = Field(..., ge=0.0, le=100.0, description="Velocity risk score [0, 100]")
    projected_exposure: float = Field(default=0.0, ge=0.0)
    trend_direction: str = Field(default="accelerating", description="'accelerating', 'stable', 'decelerating'")


# ── G: Unified Risk ─────────────────────────────────────────────────

class UnifiedRiskScoreInput(BaseModel):
    """Unified multi-component risk output for an entity."""
    entity_type: str = Field(default="provider")
    entity_id: str = Field(..., min_length=1)
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Calibrated unified risk score [0, 100]")
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rule_score: float = Field(default=0.0, ge=0.0, le=1.0)
    network_score: float = Field(default=0.0, ge=0.0, le=1.0)
    future_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence_strength: float = Field(default=0.80, ge=0.0, le=1.0)


# ── H & I: Cases & Case Evidence ────────────────────────────────────

class CaseInput(BaseModel):
    """Aggregated investigation case produced by upstream case builder."""
    case_id: str = Field(..., min_length=1, description="Unique case identifier (e.g., CASE-PRV-001)")
    entity_type: str = Field(default="provider")
    entity_id: str = Field(..., min_length=1)
    entity_name: str = Field(..., min_length=1)
    status: str = Field(default="NEW")
    priority: str = Field(default="MEDIUM")
    risk_score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence_strength: float = Field(default=0.80, ge=0.0, le=1.0)
    exposure_low: float = Field(default=0.0, ge=0.0)
    exposure_high: float = Field(default=0.0, ge=0.0)
    members_affected: int = Field(default=1, ge=0)
    claims_count: int = Field(default=1, ge=0)
    why_flagged: List[str] = Field(default_factory=list)
    top_reasons: List[str] = Field(default_factory=list)
    benign_explanations: List[str] = Field(default_factory=list)
    risk_components: Dict[str, float] = Field(default_factory=dict)
    future_risk: Optional[Dict[str, Any]] = None
    network_id: Optional[str] = None
    assigned_to: Optional[str] = None

    @field_validator("exposure_high")
    @classmethod
    def check_exposure_bounds(cls, v: float, info) -> float:
        low = info.data.get("exposure_low", 0.0)
        if v < low:
            raise ValueError(f"exposure_high ({v}) cannot be less than exposure_low ({low})")
        return v


class CaseEvidenceInput(BaseModel):
    """Direct evidence record linked to an upstream case."""
    evidence_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    rule_id: str = Field(..., min_length=1)
    rule_name: str = Field(..., min_length=1)
    claim_id: Optional[str] = None
    entity_id: str = Field(..., min_length=1)
    field_name: Optional[str] = None
    field_value: Optional[str] = None
    plain_text: str = Field(..., min_length=1)
    est_overpay: float = Field(default=0.0, ge=0.0)
    severity: str = Field(default="MEDIUM")
    source_table: str = Field(default="alerts")
    source_artifact: Optional[str] = None
    timestamp: Optional[str] = None
    fp_notes: Optional[str] = None


# ── J: Queue Items ──────────────────────────────────────────────────

class QueueItemInput(BaseModel):
    """Prioritized queue item produced by upstream SIU queue builder."""
    case_id: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1, description="Priority rank (1 = highest)")
    baseline_rank: Optional[int] = Field(default=None, ge=1)
    entity_type: str = Field(default="provider")
    entity_id: str = Field(..., min_length=1)
    entity_name: str = Field(..., min_length=1)
    risk: float = Field(..., ge=0.0, le=100.0)
    priority: str = Field(default="MEDIUM")
    exposure_low: float = Field(default=0.0, ge=0.0)
    exposure_high: float = Field(default=0.0, ge=0.0)
    members_affected: int = Field(default=1, ge=0)
    severity: str = Field(default="MEDIUM")
    evidence_strength: float = Field(default=0.80, ge=0.0, le=1.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    effort_hours: float = Field(default=2.0, ge=0.1)
    ev_per_hour: float = Field(default=0.0, ge=0.0)
    slot: int = Field(default=1, ge=1)
    top_reasons: List[str] = Field(default_factory=list)


# ── K: Evaluation Results ───────────────────────────────────────────

class EvaluationResultInput(BaseModel):
    """Ground truth benchmark or ablation evaluation metrics."""
    eval_id: str = Field(..., min_length=1)
    eval_type: str = Field(default="pipeline_evaluation", description="'rules', 'rings', 'ablation', etc.")
    metrics: Dict[str, Any] = Field(..., description="Metrics dictionary (e.g. precision, recall, ring_recovery)")
