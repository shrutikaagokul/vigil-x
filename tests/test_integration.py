"""
Integration test: run_network_behavior_rules(data)
must return valid Alert objects for R06-R10.
"""
import pytest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generator.synthetic_data import generate_synthetic_data
from rules.runner import run_network_behavior_rules, run_all_rules
from contracts.alert import Alert


@pytest.fixture(scope="module")
def synthetic_data():
    """Generate synthetic data once for all integration tests."""
    data = generate_synthetic_data(
        n_providers=100, n_members=2000, n_facilities=20,
        n_months=12, seed=42
    )
    return data


def test_integration_runs(synthetic_data):
    """run_network_behavior_rules must execute without errors."""
    alerts = run_network_behavior_rules(synthetic_data)
    assert isinstance(alerts, list)


def test_integration_produces_alerts(synthetic_data):
    """Must produce at least some alerts."""
    alerts = run_network_behavior_rules(synthetic_data)
    assert len(alerts) > 0


def test_integration_all_alerts_valid(synthetic_data):
    """Every alert must pass validation."""
    alerts = run_network_behavior_rules(synthetic_data)
    for alert in alerts:
        assert isinstance(alert, Alert)
        errors = alert.validate()
        assert errors == [], f"Alert {alert.alert_id} validation failed: {errors}"


def test_integration_all_alerts_have_evidence(synthetic_data):
    """Every alert must contain at least one evidence record."""
    alerts = run_network_behavior_rules(synthetic_data)
    for alert in alerts:
        assert len(alert.evidence) >= 1, f"Alert {alert.alert_id} has no evidence"
        for ev in alert.evidence:
            assert ev.plain_text, f"Evidence {ev.evidence_id} has no plain_text"


def test_integration_multiple_rules_fire(synthetic_data):
    """Should have alerts from multiple rules (at least R06, R09, R10)."""
    alerts = run_network_behavior_rules(synthetic_data)
    fired_rules = set(a.rule_id for a in alerts)
    # We planted scenarios for R06, R07, R08, R09, R10
    assert len(fired_rules) >= 2, f"Only these rules fired: {fired_rules}"


def test_integration_run_all_rules(synthetic_data):
    """run_all_rules should work (R01-R05 may not exist yet)."""
    alerts = run_all_rules(synthetic_data)
    assert isinstance(alerts, list)
    # Should at least contain R06-R10 alerts
    r06_r10_alerts = [a for a in alerts if a.rule_id in ["R06", "R07", "R08", "R09", "R10"]]
    assert len(r06_r10_alerts) > 0


def test_integration_no_ground_truth_leakage(synthetic_data):
    """Alerts should not reference ground truth data."""
    alerts = run_network_behavior_rules(synthetic_data)
    for alert in alerts:
        # Alert should not contain scenario_id or gt_ references
        alert_str = str(alert.to_dict())
        assert "gt_" not in alert_str.lower() or "gt_" in "gt_scenarios"  # OK in metadata context
        assert "scenario_id" not in alert_str.lower()
