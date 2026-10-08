"""
Tests for R01 — Duplicate Billing Detection.

Covers:
  1. Exact duplicate detected
  2. Near duplicate detected
  3. Corrected claim excluded
  4. Void claim excluded
  5. Legitimate modifier excluded
  6. Different member not flagged
  7. Different CPT not flagged
  8. Empty claims handled
"""

import pandas as pd
import pytest

from vigilx.models.alert import Severity
from vigilx.rules.r01_duplicate_billing import DuplicateBillingRule

# Inline config to avoid YAML dependency in tests
_TEST_CONFIG = {
    "rules": {
        "R01": {
            "enabled": True,
            "version": "1.0",
            "severity_exact": "HIGH",
            "severity_near": "MEDIUM",
            "near_dup_day_window": 1,
            "legitimate_modifiers": ["LT", "RT", "50", "76", "77"],
            "void_statuses": ["voided", "void", "reversed"],
            "corrected_statuses": ["corrected", "adjusted", "replacement"],
        }
    }
}


def _make_claims(rows: list[dict]) -> pd.DataFrame:
    """Build a claims DataFrame from row dicts."""
    df = pd.DataFrame(rows)
    df["service_from"] = pd.to_datetime(df["service_from"])
    return df


class TestR01ExactDuplicate:
    """Test exact duplicate detection."""

    def test_exact_duplicate_detected(self):
        """Two identical claims → one HIGH alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
            {"claim_id": "C002", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        assert len(alerts) >= 1
        alert = alerts[0]
        assert alert.rule_id == "R01"
        assert alert.severity == Severity.HIGH
        assert "C001" in alert.claim_ids and "C002" in alert.claim_ids
        assert alert.est_dollars == 150.0
        assert len(alert.evidence) >= 1
        assert "Exact duplicate" in alert.evidence[0].plain_text

    def test_different_member_not_flagged(self):
        """Same CPT/provider/date but different member → no alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
            {"claim_id": "C002", "member_id": "M2", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0

    def test_different_cpt_not_flagged(self):
        """Same member/provider/date but different CPT → no alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
            {"claim_id": "C002", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99214", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0


class TestR01NearDuplicate:
    """Test near-duplicate detection."""

    def test_near_duplicate_detected(self):
        """Same claim 1 day apart → MEDIUM alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
            {"claim_id": "C002", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-16", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        assert len(alerts) >= 1
        alert = alerts[0]
        assert alert.severity == Severity.MEDIUM
        assert "Near duplicate" in alert.evidence[0].plain_text


class TestR01Exclusions:
    """Test that legitimate claims are excluded."""

    def test_corrected_claim_excluded(self):
        """Corrected claim should not trigger alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "corrected", "modifier": None},
            {"claim_id": "C002", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": None},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0

    def test_void_claim_excluded(self):
        """Voided claim should not trigger alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "voided", "modifier": None},
            {"claim_id": "C002", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "voided", "modifier": None},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0

    def test_legitimate_modifier_excluded(self):
        """LT/RT modifier should not trigger alert."""
        claims = _make_claims([
            {"claim_id": "C001", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": "LT"},
            {"claim_id": "C002", "member_id": "M1", "billing_provider_id": "P1",
             "cpt_code": "99213", "service_from": "2024-01-15", "billed_amount": 150.0,
             "claim_status": "paid", "modifier": "RT"},
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0

    def test_empty_claims(self):
        """Empty claims DataFrame → no alerts."""
        claims = pd.DataFrame(columns=[
            "claim_id", "member_id", "billing_provider_id", "cpt_code",
            "service_from", "billed_amount", "claim_status", "modifier",
        ])
        rule = DuplicateBillingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0
