"""
Investigation, Case, Queue, and GenAI Brief Contracts for Vigil-X.

All models adhere to Pydantic v2 and ensure evidence provenance across the platform.
Every API response contract incorporates as_of and synthetic=True.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def get_current_as_of() -> str:
    """Return standard ISO UTC timestamp for as_of fields."""
    return datetime.now(timezone.utc).isoformat()


class BaseApiResponse(BaseModel):
    """Base response model including required provenance metadata."""
    as_of: str = Field(default_factory=get_current_as_of)
    synthetic: bool = True


class CaseStatus(str, Enum):
    NEW = "NEW"
    IN_REVIEW = "IN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class DecisionType(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ESCALATE_FOR_REVIEW = "escalate_for_review"


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Case & Evidence Contracts ──────────────────────────────────────

class CaseEvidenceItem(BaseModel):
    """A granular, traceable piece of evidence attached to an investigation case."""
    evidence_id: str
    rule_id: str
    rule_name: str
    claim_id: Optional[str] = None
    entity_id: str
    field_name: Optional[str] = None
    field_value: Optional[str] = None
    plain_text: str
    est_overpay: Optional[float] = None
    severity: str = "MEDIUM"
    source_table: str = "alerts"
    source_artifact: Optional[str] = None
    timestamp: Optional[str] = None
    fp_notes: Optional[str] = None
    currency: Optional[str] = "USD"


class CaseHeader(BaseModel):
    """Top-level investigation case header."""
    case_id: str
    entity_type: str  # "provider", "network", "facility"
    entity_id: str
    entity_name: str
    status: CaseStatus = CaseStatus.NEW
    priority: PriorityLevel = PriorityLevel.MEDIUM
    risk_score: float = Field(ge=0.0, le=100.0, description="Unified risk score (0-100)")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    exposure_low: Optional[float] = 0.0
    exposure_high: Optional[float] = 0.0
    currency: str = "USD"
    members_affected: Optional[int] = 0
    claims_count: int = 0
    why_flagged: List[str] = Field(default_factory=list)
    top_reasons: List[str] = Field(default_factory=list)
    benign_explanations: List[str] = Field(default_factory=list)
    risk_components: Dict[str, float] = Field(default_factory=dict)
    future_risk: Optional[Dict[str, Any]] = None
    network_id: Optional[str] = None
    assigned_to: Optional[str] = None
    created_at: str = Field(default_factory=get_current_as_of)
    updated_at: str = Field(default_factory=get_current_as_of)


class CaseDetail(CaseHeader):
    """Complete investigation case with nested evidence, timeline, and alerts."""
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[CaseEvidenceItem] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    network_summary: Optional[Dict[str, Any]] = None
    claims: List[Dict[str, Any]] = Field(default_factory=list)


# ── Queue Contract ──────────────────────────────────────────────────

class QueueItem(BaseModel):
    """Worklist queue item prioritized for SIU investigator review."""
    case_id: str
    rank: int
    baseline_rank: Optional[int] = None
    entity_type: str
    entity_id: str
    entity_name: str
    risk: float
    priority: PriorityLevel
    exposure_low: Optional[float] = 0.0
    exposure_high: Optional[float] = 0.0
    members_affected: Optional[int] = 0
    severity: str
    evidence_strength: float
    confidence: float
    effort_hours: float
    ev_per_hour: float
    slot: int
    top_reasons: List[str] = Field(default_factory=list)
    capacity_selected: bool = True
    queue_status: str = "QUEUED"
    capacity_rank: Optional[int] = None
    queue_id: Optional[str] = None
    currency: str = "USD"


class QueueResponse(BaseApiResponse):
    total_cases: int
    capacity_hours: float
    horizon_days: int
    sort_applied: str
    items: List[QueueItem]


# ── Evidence Packet & GenAI Brief ───────────────────────────────────

class EvidencePacket(BaseModel):
    """Structured, verified evidence payload passed to GenAI narrator."""
    case_id: str
    entity_type: str
    entity_id: str
    entity_name: str
    risk_score: float
    risk_components: Dict[str, float] = Field(default_factory=dict)
    evidence_strength: float
    confidence: float
    exposure: float
    exposure_low: float
    exposure_high: float
    members_affected: int
    top_reasons: List[str] = Field(default_factory=list)
    rule_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    ml_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    network_evidence: Dict[str, Any] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    relevant_claims: List[Dict[str, Any]] = Field(default_factory=list)
    benign_explanations: List[str] = Field(default_factory=list)
    future_risk_signals: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    # Whitelisted factual boundaries for deterministic verification
    cited_claim_ids: List[str] = Field(default_factory=list)
    cited_provider_ids: List[str] = Field(default_factory=list)
    cited_member_ids: List[str] = Field(default_factory=list)
    cited_rule_ids: List[str] = Field(default_factory=list)
    cited_network_ids: List[str] = Field(default_factory=list)
    as_of: str = Field(default_factory=get_current_as_of)
    synthetic: bool = True


class VerificationResult(BaseModel):
    """Deterministic verification report for a generated brief."""
    verified: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checked_claims: int = 0
    checked_providers: int = 0
    checked_members: int = 0
    checked_rules: int = 0
    checked_networks: int = 0
    checked_amounts: int = 0
    generation_mode: str = "fallback"


class InvestigationBrief(BaseModel):
    """GenAI or deterministic investigation brief."""
    case_id: str
    title: str
    why_prioritized: str
    evidence_narrative: str
    network_context: str
    financial_member_impact: str
    recommended_steps: List[str] = Field(default_factory=list)
    benign_explanations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    generation_mode: str = "fallback"  # "llm" or "fallback"
    generated_by: str = "deterministic_fallback"  # "llm" or "deterministic_fallback"
    verified: bool = False
    verification_report: VerificationResult
    as_of: str = Field(default_factory=get_current_as_of)
    synthetic: bool = True


# ── Q&A, Decisions & Audit ──────────────────────────────────────────

class QuestionRequest(BaseModel):
    case_id: str
    question: str


class QuestionResponse(BaseApiResponse):
    case_id: str
    question: str
    matched_intent: str
    answer: str
    grounded_facts: Dict[str, Any] = Field(default_factory=dict)
    citations: List[str] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    case_id: str
    decision: DecisionType
    notes: Optional[str] = ""
    actor: str = "investigator"


class DecisionResponse(BaseApiResponse):
    case_id: str
    status: CaseStatus
    decision: str
    recorded_at: str
    audit_id: str
    message: str


class AuditLogEntry(BaseModel):
    log_id: str
    case_id: str
    action: str
    decision: Optional[str] = None
    actor: str
    notes: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: str


# ── Summary & Evaluation Contracts ──────────────────────────────────

class SummaryFunnel(BaseModel):
    claims_ingested: int
    rules_fired: int
    alerts_produced: int
    cases_formed: int
    queue_prioritized: int


class SummaryResponse(BaseApiResponse):
    claims_analyzed: int
    lines_analyzed: int
    paid_total: float
    currency: str = "USD"
    alerts_total: int
    entity_cases: int
    network_cases: int
    queue_size: int
    funnel: SummaryFunnel


class MetricScore(BaseModel):
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int


class ScenarioResult(BaseModel):
    scenario_id: str
    scenario_type: str
    description: str
    ring_id: Optional[str] = None
    expected_rules: List[str] = Field(default_factory=list)
    detected: bool
    recovery_jaccard: Optional[float] = None
    providers_count: int
    providers_detected: int


class EvaluationResponse(BaseApiResponse):
    evaluated_at: str
    total_claims_evaluated: int
    total_providers_evaluated: int
    total_scenarios: int
    detected_scenarios: int
    scenario_recall: float
    claim_metrics: MetricScore
    provider_metrics: MetricScore
    ring_recovery_mean_jaccard: float
    scenario_breakdown: List[ScenarioResult] = Field(default_factory=list)
    rule_performance: Dict[str, MetricScore] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    benchmark_mode: str = "synthetic_benchmark"
    evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    total_evaluations: int = 1
