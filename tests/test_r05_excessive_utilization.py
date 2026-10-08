"""
Tests for R05 — Excessive Utilization Detection.

Covers:
  1. Member exceeding 30-day rolling utilization cap (e.g. PT > 12 sessions)
  2. Member within limit is not flagged
  3. Provider with visits/member > 3x peer median is flagged
  4. Normal providers within peer range are not flagged
  5. Empty inputs and edge cases
"""

import pandas as pd
import pytest

from vigilx.models.alert import Severity
from vigilx.rules.r05_excessive_utilization import ExcessiveUtilizationRule

_TEST_CONFIG = {
    "rules": {
        "R05": {
            "enabled": True,
            "version": "1.0",
            "base_severity": "MEDIUM",
            "escalated_severity": "HIGH",
            "provider_peer_multiplier": 3.0,
            "utilization_caps": {
                "physical_therapy": {
                    "code_prefixes": ["97110", "97140"],
                    "max_per_30d": 12,
                },
                "chiropractic": {
                    "code_prefixes": ["98940"],
                    "max_per_30d": 10,
                },
            },
        }
    }
}


class TestR05ExcessiveUtilization:

    def test_member_exceeding_30d_cap(self):
        """Member with 15 PT visits within 30 days exceeds max_per_30d of 12."""
        rows = []
        for i in range(15):
            rows.append({
                "claim_id": f"C_PT_{i}",
                "member_id": "M_EXCESSIVE",
                "billing_provider_id": "P_PT",
                "cpt_code": "97110",
                "service_from": pd.Timestamp("2024-03-01") + pd.Timedelta(days=i),
                "allowed_amount": 80.0,
            })
        claims = pd.DataFrame(rows)

        rule = ExcessiveUtilizationRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        member_alerts = [a for a in alerts if a.entity_type == "member" and a.entity_id == "M_EXCESSIVE"]
        assert len(member_alerts) == 1
        assert member_alerts[0].severity == Severity.MEDIUM
        assert "15" in member_alerts[0].evidence[0].plain_text
        assert member_alerts[0].est_dollars > 0

    def test_member_within_cap_not_flagged(self):
        """Member with 8 PT visits within 30 days is below max_per_30d of 12."""
        rows = []
        for i in range(8):
            rows.append({
                "claim_id": f"C_PT_{i}",
                "member_id": "M_NORMAL",
                "billing_provider_id": "P_PT",
                "cpt_code": "97110",
                "service_from": pd.Timestamp("2024-03-01") + pd.Timedelta(days=i * 2),
                "allowed_amount": 80.0,
            })
        claims = pd.DataFrame(rows)

        rule = ExcessiveUtilizationRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        member_alerts = [a for a in alerts if a.entity_type == "member"]
        assert len(member_alerts) == 0

    def test_provider_excessive_visits_per_member(self):
        """Provider with 15 visits/member vs peer median of 2 is flagged."""
        # Provider P_HIGH: 1 member with 20 claims -> 20 visits/member
        high_rows = [
            {
                "claim_id": f"C_H_{i}",
                "member_id": "M_ONE",
                "billing_provider_id": "P_HIGH",
                "cpt_code": "99213",
                "service_from": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i * 10),
                "allowed_amount": 100.0,
            }
            for i in range(20)
        ]

        # Normal peers: ~2 visits/member
        peer_rows = []
        for p_idx in range(1, 5):
            for m_idx in range(10):
                for v_idx in range(2):
                    peer_rows.append({
                        "claim_id": f"C_P{p_idx}_{m_idx}_{v_idx}",
                        "member_id": f"M_NORM_{p_idx}_{m_idx}",
                        "billing_provider_id": f"P_PEER_{p_idx}",
                        "cpt_code": "99213",
                        "service_from": pd.Timestamp("2024-01-01") + pd.Timedelta(days=v_idx * 30),
                        "allowed_amount": 100.0,
                    })

        claims = pd.DataFrame(high_rows + peer_rows)
        rule = ExcessiveUtilizationRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        prov_alerts = [a for a in alerts if a.entity_type == "provider" and a.entity_id == "P_HIGH"]
        assert len(prov_alerts) >= 1
        assert prov_alerts[0].severity == Severity.HIGH

    def test_empty_inputs(self):
        """Empty claims produces no alerts."""
        rule = ExcessiveUtilizationRule(config=_TEST_CONFIG)
        assert rule.detect({}) == []
        assert rule.detect({"claims": pd.DataFrame()}) == []
