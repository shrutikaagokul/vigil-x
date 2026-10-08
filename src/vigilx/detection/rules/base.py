"""
Abstract base rule for Detection & Behavioral Intelligence rules (R01-R10).

This base class bridges the detection/ layer with the mature vigilx.rules.base
architecture. Rules in this layer can use either the DataContext interface
(for quick dict-based evaluation) or the full pandas-based detect() interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from vigilx.detection.models.outputs import Alert, Evidence
from vigilx.rules.base import load_rules_config


class DataContext:
    """
    Holds the necessary context for rules to evaluate claims and providers.
    Contains claims, historical baselines, provider profiles, and optional
    enrichment data (members, facilities, referrals).
    """
    def __init__(
        self,
        claims: List[Dict[str, Any]],
        provider_profiles: Dict[str, Any],
        members: Optional[List[Dict[str, Any]]] = None,
        facilities: Optional[List[Dict[str, Any]]] = None,
        referrals: Optional[List[Dict[str, Any]]] = None,
    ):
        self.claims = claims
        self.provider_profiles = provider_profiles
        self.members = members or []
        self.facilities = facilities or []
        self.referrals = referrals or []


class RuleResult:
    """
    The internal result returned by a rule before being compiled into final Alerts/Evidence.
    """
    def __init__(self, triggered: bool, evidence_data: Dict[str, Any] = None):
        self.triggered = triggered
        self.evidence_data = evidence_data or {}


class BaseRule(ABC):
    """
    Base class for all Detection & Behavioral Intelligence rules (R01-R10).

    Now loads config from rules_config.yaml and supports:
    - Configurable thresholds (no magic numbers)
    - Enabled/disabled toggle
    - Rule versioning
    """
    rule_id: str = ""
    rule_name: str = ""
    rule_version: str = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            try:
                config = load_rules_config()
            except Exception:
                config = {}
        self.cfg = config.get(self.rule_id, {})
        self.enabled = self.cfg.get("enabled", True)
        self.rule_version = self.cfg.get("version", self.rule_version)

    @abstractmethod
    def evaluate(self, context: DataContext) -> List[RuleResult]:
        """
        Evaluate the rule against the provided data context.

        Args:
            context (DataContext): Data context containing claims and provider history.

        Returns:
            List[RuleResult]: A list of results indicating if the rule triggered
                              and related evidence data.
        """
        pass
