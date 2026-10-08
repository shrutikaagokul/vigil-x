"""
Data contracts, enumerations, and schemas for the Vigil-X Unified Risk Engine.

This module defines the public contracts and dataclasses for provider-level
risk scoring, evidence strength, confidence indicators, and signal tracking.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskTier(str, Enum):
    """
    Risk prioritization tiers.
    
    IMPORTANT: This is a risk prioritization score for human investigators,
    NOT a confirmation or determination of fraud.
    """
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceTier(str, Enum):
    """
    Evidence strength tiers indicating the depth and breadth of supporting data.
    """
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class ConfidenceTier(str, Enum):
    """
    Confidence tiers indicating signal availability and cross-signal agreement.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class SignalComponents:
    """
    Normalized [0, 1] risk components across all signal families.
    """
    rule_component: float = 0.0
    ml_component: float = 0.0
    anomaly_component: float = 0.0
    network_component: float = 0.0
    temporal_component: float = 0.0
    historical_component: float = 0.0
    future_component: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class SignalContributions:
    """
    Weighted contributions of each signal family to the final unified risk score.
    Must reconcile with the final risk_score within numerical tolerance.
    """
    rule_contribution: float = 0.0
    ml_contribution: float = 0.0
    anomaly_contribution: float = 0.0
    network_contribution: float = 0.0
    temporal_contribution: float = 0.0
    historical_contribution: float = 0.0
    future_contribution: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def total(self) -> float:
        return (
            self.rule_contribution
            + self.ml_contribution
            + self.anomaly_contribution
            + self.network_contribution
            + self.temporal_contribution
            + self.historical_contribution
            + self.future_contribution
        )


@dataclass
class SignalAvailability:
    """
    Tracks which subsystem signals were available vs missing for a provider.
    """
    rules_available: bool = False
    ml_available: bool = False
    anomaly_available: bool = False
    network_available: bool = False
    temporal_available: bool = False
    historical_available: bool = False
    future_available: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)

    def available_count(self) -> int:
        return sum(
            1 for v in [
                self.rules_available,
                self.ml_available,
                self.anomaly_available,
                self.network_available,
                self.temporal_available,
                self.historical_available,
                self.future_available,
            ] if v
        )


@dataclass
class ProviderScoreRecord:
    """
    Stable provider-level output contract for the Vigil-X Unified Risk Engine.
    
    Contains unified risk score, risk tier, evidence strength, confidence,
    individual normalized components, weighted contributions, machine-readable
    top reasons, and granular traceability back to source alerts, claims, and networks.
    """
    provider_id: str

    # Prioritization score & tier
    risk_score: float
    risk_tier: str

    # Evidence strength & tier
    evidence_strength: float
    evidence_tier: str

    # Confidence & tier
    confidence_score: float
    confidence_tier: str

    # Normalized [0, 1] components
    rule_component: float
    ml_component: float
    anomaly_component: float
    network_component: float
    temporal_component: float
    historical_component: float
    future_component: float

    # Weighted contributions
    rule_contribution: float
    ml_contribution: float
    anomaly_contribution: float
    network_contribution: float
    temporal_contribution: float
    historical_contribution: float
    future_contribution: float

    # Explainability
    top_reasons: List[str]

    # Specific aggregated subsystem fields
    rule_alert_count: int = 0
    high_severity_rule_count: int = 0
    estimated_rule_dollars: float = 0.0

    high_risk_claim_count: int = 0
    high_risk_claim_rate: float = 0.0

    anomaly_score: float = 0.0
    anomaly_flag: int = 0

    risk_30d: float = 0.0
    risk_60d: float = 0.0
    risk_90d: float = 0.0

    community_id: Optional[int] = None

    # Traceability links
    rule_alert_ids: List[str] = field(default_factory=list)
    high_risk_claim_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)

    # Signal availability
    rules_available: bool = False
    ml_available: bool = False
    anomaly_available: bool = False
    network_available: bool = False
    temporal_available: bool = False
    historical_available: bool = False
    future_available: bool = False

    # Version metadata
    model_version: str = "1.0.0"
    feature_version: str = "1.0.0"
    risk_engine_version: str = "1.0.0"

    def to_dict(self, serialize_lists: bool = False) -> Dict[str, Any]:
        """
        Convert to flat dictionary.
        
        If serialize_lists is True, list fields are serialized to JSON strings
        for compatibility with flat tabular formats like CSV.
        """
        d = asdict(self)
        if serialize_lists:
            d["top_reasons"] = json.dumps(self.top_reasons)
            d["rule_alert_ids"] = json.dumps(self.rule_alert_ids)
            d["high_risk_claim_ids"] = json.dumps(self.high_risk_claim_ids)
            d["evidence_ids"] = json.dumps(self.evidence_ids)
        return d

    def validate(self) -> List[str]:
        """Validate score boundaries and data consistency."""
        errors = []
        if not self.provider_id:
            errors.append("provider_id is required")
        if not (0.0 <= self.risk_score <= 1.0):
            errors.append(f"risk_score {self.risk_score} is outside [0, 1]")
        if not (0.0 <= self.evidence_strength <= 1.0):
            errors.append(f"evidence_strength {self.evidence_strength} is outside [0, 1]")
        if not (0.0 <= self.confidence_score <= 1.0):
            errors.append(f"confidence_score {self.confidence_score} is outside [0, 1]")
        if self.risk_tier not in [t.value for t in RiskTier]:
            errors.append(f"invalid risk_tier: {self.risk_tier}")
        if self.evidence_tier not in [t.value for t in EvidenceTier]:
            errors.append(f"invalid evidence_tier: {self.evidence_tier}")
        if self.confidence_tier not in [t.value for t in ConfidenceTier]:
            errors.append(f"invalid confidence_tier: {self.confidence_tier}")
        return errors
