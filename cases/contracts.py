"""
Data contracts, enumerations, and schemas for the Vigil-X Case Builder subsystem.

Defines the core data contracts for investigation cases, case evidence items,
case priorities, and lifecycle statuses.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CaseStatus(str, Enum):
    """
    Controlled lifecycle statuses for investigation cases.
    
    IMPORTANT: Cases are investigative artifacts. Never automatically mark as 'CONFIRMED_FRAUD'.
    """
    NEW = "NEW"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class CasePriority(str, Enum):
    """
    Operational priority assigned to an investigation case for SIU triage.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class NetworkRelationship:
    """
    Represents an observed structural relationship with an affiliated entity.
    """
    provider_id: str
    relationship: str
    strength: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CaseEvidenceRecord:
    """
    Granular evidence record attached to an investigation case.
    
    Preserves one-to-many relationships between a case and supporting signals
    (rule alerts, claim ML scores, network links, behavioral anomalies, future forecasts).
    """
    case_id: str
    evidence_id: str
    source_type: str  # "RULE", "ML", "NETWORK", "ANOMALY", "FUTURE_RISK"
    source_id: str
    provider_id: str
    claim_id: Optional[str] = None
    rule_id: Optional[str] = None
    description: str = ""
    severity: str = "MEDIUM"
    estimated_amount: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> List[str]:
        errors = []
        if not self.case_id:
            errors.append("case_id is required")
        if not self.evidence_id:
            errors.append("evidence_id is required")
        if not self.source_type:
            errors.append("source_type is required")
        if not self.provider_id:
            errors.append("provider_id is required")
        return errors


@dataclass
class InvestigationCase:
    """
    Consolidated investigation case representing a prioritized provider target.
    
    Contains all consolidated risk scores, evidence summaries, audit claims,
    alert references, network relationships, and actionable recommendations.
    """
    case_id: str
    provider_id: str

    title: str
    summary: str

    # Prioritization scores from Unified Risk Engine
    risk_score: float
    risk_tier: str

    evidence_strength: float
    evidence_tier: str

    confidence_score: float
    confidence_tier: str

    estimated_exposure: float

    status: str = CaseStatus.NEW.value
    priority: str = CasePriority.MEDIUM.value

    created_at: str = ""
    updated_at: str = ""

    community_id: Optional[int] = None

    claim_count: int = 0
    high_risk_claim_count: int = 0

    rule_alert_count: int = 0
    high_severity_rule_count: int = 0
    distinct_rule_count: int = 0

    anomaly_score: Optional[float] = None
    anomaly_flag: Optional[int] = None

    risk_30d: Optional[float] = None
    risk_60d: Optional[float] = None
    risk_90d: Optional[float] = None

    top_reasons: List[str] = field(default_factory=list)
    signal_families: List[str] = field(default_factory=list)

    claim_ids: List[str] = field(default_factory=list)
    alert_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)

    network_relationships: List[Dict[str, Any]] = field(default_factory=list)
    investigation_recommendations: List[str] = field(default_factory=list)

    # Version metadata
    model_version: str = "1.0.0"
    feature_version: str = "1.0.0"
    risk_engine_version: str = "1.0.0"
    case_builder_version: str = "1.0.0"

    def to_dict(self, serialize_lists: bool = False) -> Dict[str, Any]:
        """
        Convert to flat dictionary.
        
        If serialize_lists is True, list and dict fields are serialized to JSON strings
        for flat tabular formats like CSV.
        """
        d = asdict(self)
        if serialize_lists:
            for list_col in [
                "top_reasons", "signal_families", "claim_ids", "alert_ids",
                "evidence_ids", "network_relationships", "investigation_recommendations"
            ]:
                d[list_col] = json.dumps(d[list_col])
        return d

    def validate(self) -> List[str]:
        """Validate case fields and boundaries."""
        errors = []
        if not self.case_id:
            errors.append("case_id is required")
        if not self.provider_id:
            errors.append("provider_id is required")
        if not (0.0 <= self.risk_score <= 1.0):
            errors.append(f"risk_score {self.risk_score} is outside [0, 1]")
        if self.status not in [s.value for s in CaseStatus]:
            errors.append(f"invalid status: {self.status}")
        if self.priority not in [p.value for p in CasePriority]:
            errors.append(f"invalid priority: {self.priority}")

        # Check defensive language constraints
        prohibited = ["fraud confirmed", "fraudster", "committed fraud", "guilty"]
        full_text = (self.title + " " + self.summary).lower()
        for term in prohibited:
            if term in full_text:
                errors.append(f"prohibited language detected: '{term}'")

        return errors
