"""
Shared Alert / Evidence contract for Vigil-X.

Every rule (R01-R10) MUST produce alerts using these dataclasses.
This is the single source of truth for the alert schema.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class Severity(str, Enum):
    """Alert severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Evidence:
    """
    A single piece of evidence supporting an alert.

    Every number shown in the UI must be traceable back to an Evidence record.
    """
    evidence_id: str
    rule_id: str
    rule_version: str
    claim_ids: List[str]
    fields_matched: List[str]
    plain_text: str
    est_overpay: float = 0.0
    severity: str = Severity.MEDIUM.value
    fp_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def generate_id(rule_id: str, seq: int = 0) -> str:
        """Generate a deterministic evidence ID."""
        short = uuid.uuid4().hex[:8]
        return f"E-{rule_id}-{short}-{seq:03d}"


@dataclass
class Alert:
    """
    A single FWA alert produced by a detection rule.

    The system does NOT declare fraud.  It identifies suspicious indicators,
    produces evidence-backed alerts, and prioritizes them for human review.
    """
    alert_id: str
    rule_id: str
    rule_version: str
    entity_type: str          # "provider", "member", "facility"
    entity_id: str
    claim_ids: List[str]
    severity: str
    est_dollars: float
    evidence: List[Evidence]
    fp_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @staticmethod
    def generate_id(rule_id: str) -> str:
        """Generate a unique alert ID."""
        short = uuid.uuid4().hex[:8]
        return f"A-{rule_id}-{short}"

    def validate(self) -> List[str]:
        """Return a list of validation errors (empty if valid)."""
        errors = []
        if not self.alert_id:
            errors.append("alert_id is required")
        if not self.rule_id:
            errors.append("rule_id is required")
        if not self.entity_type:
            errors.append("entity_type is required")
        if not self.entity_id:
            errors.append("entity_id is required")
        if not self.evidence:
            errors.append("at least one Evidence record is required")
        if self.severity not in [s.value for s in Severity]:
            errors.append(f"invalid severity: {self.severity}")
        for ev in self.evidence:
            if not ev.plain_text:
                errors.append(f"evidence {ev.evidence_id} missing plain_text")
            if not ev.fields_matched:
                errors.append(f"evidence {ev.evidence_id} missing fields_matched")
        return errors
