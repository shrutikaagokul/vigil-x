"""
Tests for RuleRunner and runner orchestrator.

Covers:
  1. Default registration of R01-R05
  2. Independent rule execution (fault tolerance / rule isolation)
  3. Dynamic rule registration (teammate extensibility for R06-R10)
  4. Disabled rule skipping
  5. run_claim_utilization_rules public API
"""

import pandas as pd
import pytest

from vigilx.models.alert import Alert, Severity
from vigilx.rules.base import BaseRule
from vigilx.runner import RuleRunner, create_full_runner, run_claim_utilization_rules


class DummyFailingRule(BaseRule):
    rule_id = "R_FAIL"

    def detect(self, data):
        raise RuntimeError("Synthetic failure in test rule")


class DummyPassingRule(BaseRule):
    rule_id = "R_PASS"

    def detect(self, data):
        return [
            Alert(
                alert_id="A-PASS-1",
                rule_id="R_PASS",
                rule_version="1.0",
                entity_type="provider",
                entity_id="PRV_TEST",
                claim_ids=["C1"],
                severity=Severity.LOW,
                est_dollars=0.0,
                evidence=[],
            )
        ]


class TestRuleRunner:

    def test_fault_tolerance(self):
        """Runner catches exceptions from faulty rules without stopping others."""
        runner = RuleRunner(config={"rules": {}})
        runner.register(DummyFailingRule)
        runner.register(DummyPassingRule)

        alerts = runner.run({})
        assert len(alerts) == 1
        assert alerts[0].rule_id == "R_PASS"

    def test_disabled_rule_skipped(self):
        """Rules with enabled: False are not executed."""
        runner = RuleRunner(config={"rules": {"R_PASS": {"enabled": False}}})
        runner.register(DummyPassingRule)

        alerts = runner.run({})
        assert len(alerts) == 0

    def test_extensibility_for_r06_r10(self):
        """create_full_runner allows adding R06-R10 rules via register()."""
        runner = create_full_runner()
        initial_rule_count = len(runner.rules)
        assert initial_rule_count == 5  # R01-R05

        class DummyR06(BaseRule):
            rule_id = "R06"

            def detect(self, data):
                return []

        runner.register(DummyR06)
        assert len(runner.rules) == initial_rule_count + 1
        assert runner.rules[-1].rule_id == "R06"

    def test_run_claim_utilization_rules_empty_data(self):
        """Public runner function runs cleanly on empty data."""
        alerts = run_claim_utilization_rules({"claims": pd.DataFrame()})
        assert alerts == []
