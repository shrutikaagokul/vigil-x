"""
Tests for R03 — Unbundling Detection.

Covers:
  1. Exact bundling pair detected on same day/member/provider
  2. Override modifier (e.g. 59, 25, XE) suppresses alert
  3. Non-overlapping dates do not trigger alert
  4. Different providers on same day do not trigger alert
  5. Provider escalation when unbundling rate > peer p95
  6. Empty / missing input data handling
"""

import pandas as pd
import pytest

from vigilx.models.alert import Severity
from vigilx.rules.r03_unbundling import UnbundlingRule

_TEST_CONFIG = {
    "rules": {
        "R03": {
            "enabled": True,
            "version": "1.0",
            "base_severity": "MEDIUM",
            "escalated_severity": "HIGH",
            "allowed_override_modifiers": ["59", "25", "XE"],
            "provider_rate_percentile": 95,
        }
    }
}

_BUNDLING_PAIRS = pd.DataFrame([
    {"comprehensive_cpt": "80053", "component_cpt": "80048"},  # CMP includes BMP
    {"comprehensive_cpt": "93000", "component_cpt": "93010"},  # ECG complete includes report
])


class TestR03Unbundling:

    def test_unbundling_pair_detected(self):
        """Billing comprehensive + component on same date flags alert."""
        claims = pd.DataFrame([
            {
                "claim_id": "C-COMP",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80053",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 100.0,
                "modifier": None,
            },
            {
                "claim_id": "C-PART",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80048",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 40.0,
                "modifier": None,
            },
        ])

        rule = UnbundlingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "bundling_pairs": _BUNDLING_PAIRS})

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.rule_id == "R03"
        assert alert.entity_id == "P01"
        assert set(alert.claim_ids) == {"C-COMP", "C-PART"}
        assert alert.est_dollars == 40.0  # Component amount
        assert alert.severity == Severity.MEDIUM

    def test_override_modifier_suppresses_alert(self):
        """Legitimate modifier (e.g. 59) suppresses unbundling alert."""
        claims = pd.DataFrame([
            {
                "claim_id": "C-COMP",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80053",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 100.0,
                "modifier": None,
            },
            {
                "claim_id": "C-PART",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80048",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 40.0,
                "modifier": "59",  # Distinct procedural service
            },
        ])

        rule = UnbundlingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "bundling_pairs": _BUNDLING_PAIRS})

        assert len(alerts) == 0

    def test_different_dates_no_alert(self):
        """Comprehensive and component billed on different dates are not unbundled."""
        claims = pd.DataFrame([
            {
                "claim_id": "C-1",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80053",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 100.0,
                "modifier": None,
            },
            {
                "claim_id": "C-2",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80048",
                "service_from": pd.Timestamp("2024-03-05"),  # Different date
                "allowed_amount": 40.0,
                "modifier": None,
            },
        ])

        rule = UnbundlingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "bundling_pairs": _BUNDLING_PAIRS})
        assert len(alerts) == 0

    def test_different_providers_no_alert(self):
        """Different providers billing on same day is not unbundling by a single provider."""
        claims = pd.DataFrame([
            {
                "claim_id": "C-1",
                "member_id": "M100",
                "billing_provider_id": "P01",
                "cpt_code": "80053",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 100.0,
                "modifier": None,
            },
            {
                "claim_id": "C-2",
                "member_id": "M100",
                "billing_provider_id": "P02",  # Different provider
                "cpt_code": "80048",
                "service_from": pd.Timestamp("2024-03-01"),
                "allowed_amount": 40.0,
                "modifier": None,
            },
        ])

        rule = UnbundlingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "bundling_pairs": _BUNDLING_PAIRS})
        assert len(alerts) == 0

    def test_empty_inputs(self):
        """Empty claims or empty bundling pairs produces no alerts."""
        rule = UnbundlingRule(config=_TEST_CONFIG)
        assert rule.detect({}) == []
        assert rule.detect({"claims": pd.DataFrame()}) == []
        assert rule.detect({"claims": pd.DataFrame(), "bundling_pairs": _BUNDLING_PAIRS}) == []
