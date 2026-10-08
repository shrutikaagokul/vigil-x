"""
Shared Alert and Evidence contract for Vigil-X.

Every rule (R01–R10) MUST return List[Alert] using these models.
This is the single source of truth for alert structure across the platform.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Alert severity levels, ordered from lowest to highest."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def __ge__(self, other: "Severity") -> bool:
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) >= order.index(other)

    def __gt__(self, other: "Severity") -> bool:
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) > order.index(other)

    def __le__(self, other: "Severity") -> bool:
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) <= order.index(other)

    def __lt__(self, other: "Severity") -> bool:
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) < order.index(other)


def _make_id(prefix: str = "E") -> str:
    """Generate a short unique ID with a prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@dataclass
class Evidence:
    """
    A single piece of evidence supporting an alert.

    Every evidence item must explain WHY the alert fired, with
    traceable claim IDs, matched fields, and human-readable text.
    """

    evidence_id: str
    rule_id: str
    rule_version: str
    claim_ids: list[str]
    fields_matched: list[str]
    plain_text: str
    est_overpay: float = 0.0
    severity: Severity = Severity.MEDIUM
    fp_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "evidence_id": self.evidence_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "claim_ids": self.claim_ids,
            "fields_matched": self.fields_matched,
            "plain_text": self.plain_text,
            "est_overpay": self.est_overpay,
            "severity": self.severity.value,
            "fp_notes": self.fp_notes,
        }


@dataclass
class Alert:
    """
    A standardized alert produced by any Vigil-X detection rule.

    Alerts are the universal currency of the pipeline: every rule
    produces them, and the downstream risk engine consumes them
    without caring which rule generated them.
    """

    alert_id: str
    rule_id: str
    rule_version: str
    entity_type: str  # "provider", "member", "facility"
    entity_id: str
    claim_ids: list[str]
    severity: Severity
    est_dollars: float
    evidence: list[Evidence]
    fp_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "claim_ids": self.claim_ids,
            "severity": self.severity.value,
            "est_dollars": self.est_dollars,
            "evidence": [e.to_dict() for e in self.evidence],
            "fp_notes": self.fp_notes,
        }

    @staticmethod
    def make_id() -> str:
        """Generate a unique alert ID."""
        return _make_id("A")


def make_evidence_id(rule_id: str) -> str:
    """Generate a unique evidence ID prefixed with the rule ID."""
    return f"E-{rule_id}-{uuid.uuid4().hex[:8]}"
