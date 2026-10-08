"""
Data contracts and schemas for the Vigil-X SIU Priority Queue subsystem.

Defines the core data contracts for SIU Queue items, operational priority tiers,
queue lifecycle statuses, and validation rules.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SIUPriorityTier(str, Enum):
    """Operational triage priority tier for SIU investigation scheduling."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SIUQueueStatus(str, Enum):
    """Operational queue lifecycle status for an investigation case."""
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    DEFERRED = "DEFERRED"
    COMPLETED = "COMPLETED"


PROHIBITED_TERMS = [
    "fraud confirmed",
    "confirmed fraud",
    "fraudster",
    "committed fraud",
    "guilty",
]


@dataclass
class SIUQueueItem:
    """
    Capacity-aware SIU Queue item representing a prioritized investigation case.
    
    Contains operational priority ranking, multi-signal scores, capacity allocation,
    traceable explanation reasons, and provenance metadata.
    """
    queue_id: str
    case_id: str
    provider_id: str

    rank: int

    priority_score: float
    priority_tier: str

    risk_score: float
    risk_tier: str

    evidence_strength: float
    confidence_score: float

    estimated_exposure: float

    network_signal: float
    anomaly_signal: float
    future_risk_signal: float
    behavioral_signal: float

    case_status: str
    queue_status: str

    capacity_selected: bool
    capacity_rank: int

    priority_reasons: List[str] = field(default_factory=list)

    claim_count: int = 0
    alert_count: int = 0
    evidence_count: int = 0

    community_id: Optional[int] = None

    created_at: str = ""
    queued_at: str = ""

    case_builder_version: str = "1.0.0"
    siu_version: str = "1.0.0"

    def to_dict(self, serialize_lists: bool = False) -> Dict[str, Any]:
        """
        Convert to flat dictionary representation.
        
        If serialize_lists is True, list fields (e.g. priority_reasons)
        are serialized to JSON strings for flat CSV export.
        """
        d = asdict(self)
        if serialize_lists:
            d["priority_reasons"] = json.dumps(self.priority_reasons)
        return d

    def validate(self) -> List[str]:
        """
        Validate queue item fields and boundaries according to SIU contract rules.
        """
        errors = []

        if not self.queue_id:
            errors.append("queue_id is required")
        if not self.case_id:
            errors.append("case_id is required")
        if not self.provider_id:
            errors.append("provider_id is required")

        if not (0.0 <= self.priority_score <= 1.0):
            errors.append(f"priority_score {self.priority_score} is outside [0, 1]")

        for sig_name, sig_val in [
            ("network_signal", self.network_signal),
            ("anomaly_signal", self.anomaly_signal),
            ("future_risk_signal", self.future_risk_signal),
            ("behavioral_signal", self.behavioral_signal),
            ("risk_score", self.risk_score),
            ("evidence_strength", self.evidence_strength),
            ("confidence_score", self.confidence_score),
        ]:
            if not (0.0 <= sig_val <= 1.0):
                errors.append(f"{sig_name} {sig_val} is outside [0, 1]")

        valid_tiers = [t.value for t in SIUPriorityTier]
        if self.priority_tier not in valid_tiers:
            errors.append(f"invalid priority_tier: {self.priority_tier} (must be in {valid_tiers})")

        valid_statuses = [s.value for s in SIUQueueStatus]
        if self.queue_status not in valid_statuses:
            errors.append(f"invalid queue_status: {self.queue_status} (must be in {valid_statuses})")

        if self.rank < 1:
            errors.append(f"rank must be >= 1, got {self.rank}")

        if self.capacity_rank < 0:
            errors.append(f"capacity_rank must be >= 0, got {self.capacity_rank}")

        # Check defensive language compliance in priority_reasons
        joined_reasons = " ".join(self.priority_reasons).lower()
        for term in PROHIBITED_TERMS:
            if term in joined_reasons:
                errors.append(f"prohibited fraud-confirmation language detected in priority_reasons: '{term}'")

        return errors
