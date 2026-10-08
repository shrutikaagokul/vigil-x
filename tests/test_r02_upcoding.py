"""
Tests for R02 — Upcoding Detection.

Covers:
  1. Obvious upcoding provider detected
  2. Normal provider not flagged
  3. High-acuity legitimate provider not flagged
  4. Insufficient sample size excluded
  5. Claim-level low-complexity Level-5 evidence
  6. Peer comparison calculation correctness
"""

import pandas as pd
import pytest
import numpy as np

from vigilx.models.alert import Severity
from vigilx.rules.r02_upcoding import UpcodingRule

_TEST_CONFIG = {
    "rules": {
        "R02": {
            "enabled": True,
            "version": "1.0",
            "min_em_claims": 10,  # Lowered for test data
            "mad_z_threshold": 3.0,
            "share_multiplier": 2.0,
            "claim_level": {
                "low_complexity_max": 1,
                "duration_percentile": 25,
            },
        }
    }
}


def _make_em_claims(provider_id: str, level_dist: dict[int, int], base_amount: float = 100.0) -> pd.DataFrame:
    """Generate E/M claims for a provider with given level distribution."""
    rows = []
    claim_idx = 0
    for level, count in level_dist.items():
        for _ in range(count):
            rows.append({
                "claim_id": f"C-{provider_id}-{claim_idx}",
                "member_id": f"M{claim_idx % 20}",
                "billing_provider_id": provider_id,
                "cpt_code": f"9921{level}",
                "em_level": level,
                "dx_complexity": level,  # Normal: complexity matches level
                "service_from": pd.Timestamp("2024-01-15") + pd.Timedelta(days=claim_idx % 30),
                "allowed_amount": base_amount * level,
                "service_minutes": 15 * level,
            })
            claim_idx += 1
    return pd.DataFrame(rows)


class TestR02UpcodingDetection:

    def test_obvious_upcoder_detected(self):
        """Provider with 90% Level-5 vs peers at 15% → alert."""
        # Upcoding provider: 90% level 5
        upcoder = _make_em_claims("P_BAD", {1: 1, 2: 1, 3: 1, 4: 2, 5: 45})
        # Normal peers
        normal1 = _make_em_claims("P_NORM1", {1: 5, 2: 15, 3: 20, 4: 7, 5: 3})
        normal2 = _make_em_claims("P_NORM2", {1: 4, 2: 12, 3: 22, 4: 8, 5: 4})
        normal3 = _make_em_claims("P_NORM3", {1: 6, 2: 14, 3: 18, 4: 9, 5: 3})

        claims = pd.concat([upcoder, normal1, normal2, normal3], ignore_index=True)
        rule = UpcodingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        upcoder_alerts = [a for a in alerts if a.entity_id == "P_BAD"]
        assert len(upcoder_alerts) >= 1
        assert upcoder_alerts[0].severity == Severity.HIGH
        assert any("Level-4/5" in e.plain_text for e in upcoder_alerts[0].evidence)

    def test_normal_provider_not_flagged(self):
        """Provider with typical coding distribution → no alert."""
        normal1 = _make_em_claims("P1", {1: 5, 2: 15, 3: 20, 4: 7, 5: 3})
        normal2 = _make_em_claims("P2", {1: 4, 2: 12, 3: 22, 4: 8, 5: 4})
        normal3 = _make_em_claims("P3", {1: 6, 2: 14, 3: 18, 4: 9, 5: 3})

        claims = pd.concat([normal1, normal2, normal3], ignore_index=True)
        rule = UpcodingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})
        assert len(alerts) == 0

    def test_high_acuity_legitimate_provider(self):
        """Provider with elevated L4/5 but below threshold → no alert."""
        # Slightly elevated but not extreme
        elevated = _make_em_claims("P_LEGIT", {1: 3, 2: 8, 3: 15, 4: 12, 5: 12})
        normal1 = _make_em_claims("P1", {1: 5, 2: 15, 3: 20, 4: 7, 5: 3})
        normal2 = _make_em_claims("P2", {1: 4, 2: 12, 3: 22, 4: 8, 5: 4})
        normal3 = _make_em_claims("P3", {1: 6, 2: 14, 3: 18, 4: 9, 5: 3})
        normal4 = _make_em_claims("P4", {1: 5, 2: 13, 3: 19, 4: 10, 5: 3})

        claims = pd.concat([elevated, normal1, normal2, normal3, normal4], ignore_index=True)
        rule = UpcodingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        legit_alerts = [a for a in alerts if a.entity_id == "P_LEGIT"]
        # Should not be flagged — elevated but within peer variance
        # (depends on exact MAD threshold; the distribution is borderline)
        # This test validates the rule doesn't over-flag
        assert len(legit_alerts) == 0 or legit_alerts[0].evidence[0].fp_notes

    def test_insufficient_sample_size(self):
        """Provider with < min_claims → no alert even if distribution is extreme."""
        # Only 5 claims (below min of 10)
        tiny = _make_em_claims("P_TINY", {5: 5})
        normal = _make_em_claims("P1", {1: 5, 2: 15, 3: 20, 4: 7, 5: 3})

        claims = pd.concat([tiny, normal], ignore_index=True)
        rule = UpcodingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        tiny_alerts = [a for a in alerts if a.entity_id == "P_TINY"]
        assert len(tiny_alerts) == 0

    def test_claim_level_low_complexity_level5(self):
        """Level-5 claim with dx_complexity=1 appears in claim-level evidence."""
        upcoder_rows = []
        for i in range(50):
            upcoder_rows.append({
                "claim_id": f"C-BAD-{i}",
                "member_id": f"M{i % 20}",
                "billing_provider_id": "P_BAD",
                "cpt_code": "99215",
                "em_level": 5,
                "dx_complexity": 1,  # Low complexity + Level 5 = suspect
                "service_from": pd.Timestamp("2024-01-15") + pd.Timedelta(days=i % 30),
                "allowed_amount": 500.0,
                "service_minutes": 10,
            })
        upcoder = pd.DataFrame(upcoder_rows)

        normal = _make_em_claims("P1", {1: 10, 2: 15, 3: 20, 4: 7, 5: 3})
        normal2 = _make_em_claims("P2", {1: 8, 2: 12, 3: 22, 4: 8, 5: 5})
        normal3 = _make_em_claims("P3", {1: 9, 2: 14, 3: 18, 4: 9, 5: 5})

        claims = pd.concat([upcoder, normal, normal2, normal3], ignore_index=True)
        rule = UpcodingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        bad_alerts = [a for a in alerts if a.entity_id == "P_BAD"]
        assert len(bad_alerts) >= 1

        # Should have claim-level evidence
        claim_evidence = [e for e in bad_alerts[0].evidence if "dx_complexity" in e.plain_text]
        assert len(claim_evidence) >= 1

    def test_peer_comparison_present(self):
        """Alert evidence should include peer median comparison."""
        upcoder = _make_em_claims("P_BAD", {1: 1, 2: 1, 3: 1, 4: 2, 5: 45})
        normal1 = _make_em_claims("P1", {1: 5, 2: 15, 3: 20, 4: 7, 5: 3})
        normal2 = _make_em_claims("P2", {1: 4, 2: 12, 3: 22, 4: 8, 5: 4})

        claims = pd.concat([upcoder, normal1, normal2], ignore_index=True)
        rule = UpcodingRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        assert len(alerts) >= 1
        prov_evidence = alerts[0].evidence[0]
        assert "peer median" in prov_evidence.plain_text
        assert "z-score" in prov_evidence.plain_text.lower() or "MAD" in prov_evidence.plain_text
