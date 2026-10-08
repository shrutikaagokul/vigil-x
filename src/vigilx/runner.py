"""
Rule runner for Vigil-X detection subsystem.

Provides the public interface for running detection rules:
  - run_claim_utilization_rules(data) -> List[Alert]   (R01-R05)
  - run_all_rules(data) -> List[Alert]                 (R01-R10, when all registered)

Rules are registered into a runner and executed independently.
The R06-R10 teammate can register their rules into the same runner
without modifying any R01-R05 code.
"""

from __future__ import annotations

from typing import Any

from vigilx.models.alert import Alert
from vigilx.rules.base import BaseRule, load_rules_config
from vigilx.rules.r01_duplicate_billing import DuplicateBillingRule
from vigilx.rules.r02_upcoding import UpcodingRule
from vigilx.rules.r03_unbundling import UnbundlingRule
from vigilx.rules.r04_phantom_services import PhantomServicesRule
from vigilx.rules.r05_excessive_utilization import ExcessiveUtilizationRule


# ── Registry ─────────────────────────────────────────────────────

# R01–R05 claim/utilization rules
CLAIM_UTILIZATION_RULES: list[type[BaseRule]] = [
    DuplicateBillingRule,
    UpcodingRule,
    UnbundlingRule,
    PhantomServicesRule,
    ExcessiveUtilizationRule,
]


class RuleRunner:
    """
    Runs a set of registered detection rules against data.

    Usage:
        runner = RuleRunner()
        runner.register(MyCustomRule)
        alerts = runner.run(data)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_rules_config()
        self._rules: list[BaseRule] = []

    def register(self, rule_class: type[BaseRule]) -> None:
        """Register a rule class. It will be instantiated with the runner's config."""
        self._rules.append(rule_class(config=self.config))

    def register_instance(self, rule: BaseRule) -> None:
        """Register an already-instantiated rule."""
        self._rules.append(rule)

    @property
    def rules(self) -> list[BaseRule]:
        """Return the list of registered rule instances."""
        return list(self._rules)

    def run(self, data: dict[str, Any]) -> list[Alert]:
        """
        Execute all registered rules and return combined alerts.

        Each rule runs independently; a failure in one rule does NOT
        prevent other rules from executing.
        """
        all_alerts: list[Alert] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            try:
                alerts = rule.detect(data)
                all_alerts.extend(alerts)
            except Exception as e:
                # Log but don't crash — other rules should still run
                print(f"[WARN] Rule {rule.rule_id} failed: {e}")
        return all_alerts


def run_claim_utilization_rules(
    data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> list[Alert]:
    """
    Run R01–R05 claim/utilization detection rules.

    This is the primary public interface for the claim/utilization subsystem.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary of DataFrames keyed by table name.
    config : dict, optional
        Override config. If None, loads from default YAML.

    Returns
    -------
    list[Alert]
        All alerts produced by R01–R05.
    """
    runner = RuleRunner(config=config)
    for rule_class in CLAIM_UTILIZATION_RULES:
        runner.register(rule_class)
    return runner.run(data)


def create_full_runner(config: dict[str, Any] | None = None) -> RuleRunner:
    """
    Create a RuleRunner with R01–R05 pre-registered.

    The R06–R10 teammate can then call runner.register(TheirRule)
    to add their rules without modifying this code.
    """
    runner = RuleRunner(config=config)
    for rule_class in CLAIM_UTILIZATION_RULES:
        runner.register(rule_class)
    return runner
