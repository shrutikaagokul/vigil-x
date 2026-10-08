"""
Tests for shared feature engineering functions across claim, member, provider, and peer modules.
"""

import numpy as np
import pandas as pd
import pytest

from vigilx.features.claim_features import (
    add_claim_frequency,
    compute_rolling_30d_counts,
    extract_em_level,
)
from vigilx.features.member_features import compute_member_utilization, flag_ghost_members
from vigilx.features.peer_features import (
    compute_mad_zscore,
    compute_peer_duration_stats,
    compute_peer_stats,
)
from vigilx.features.provider_features import (
    compute_provider_em_distribution,
    compute_provider_utilization_stats,
)


class TestFeatureEngineering:

    def test_extract_em_level(self):
        claims = pd.DataFrame([
            {"cpt_code": "99213"},
            {"cpt_code": "99215"},
            {"cpt_code": "99201"},
            {"cpt_code": "99204"},
            {"cpt_code": "80053"},  # Non-EM
        ])
        res = extract_em_level(claims)
        assert res.loc[0, "em_level"] == 3
        assert res.loc[1, "em_level"] == 5
        assert res.loc[2, "em_level"] == 1
        assert res.loc[3, "em_level"] == 4
        assert pd.isna(res.loc[4, "em_level"])

    def test_rolling_30d_counts(self):
        claims = pd.DataFrame([
            {"member_id": "M1", "service_from": pd.Timestamp("2024-01-01"), "cpt_code": "99213"},
            {"member_id": "M1", "service_from": pd.Timestamp("2024-01-10"), "cpt_code": "99213"},
            {"member_id": "M1", "service_from": pd.Timestamp("2024-01-20"), "cpt_code": "99213"},
            {"member_id": "M1", "service_from": pd.Timestamp("2024-02-15"), "cpt_code": "99213"},  # > 30d from Jan 1 & 10
        ])
        res = compute_rolling_30d_counts(claims, group_cols=["member_id"])
        counts = res["rolling_30d_count"].tolist()
        assert counts[0] == 1
        assert counts[1] == 2
        assert counts[2] == 3
        assert counts[3] == 2  # Includes Jan 20 and Feb 15 (26 days apart)

    def test_compute_mad_zscore(self):
        # Series with variation around 10
        data = pd.Series([8.0, 9.0, 10.0, 11.0, 12.0, 100.0])
        z = compute_mad_zscore(data)
        # Median is 10.5. Outlier 100 should have a high z-score
        assert z.iloc[-1] > 5.0
        assert abs(z.iloc[2]) < 1.0

    def test_compute_mad_zscore_constant(self):
        # All identical values -> MAD is 0 -> should safely return 0 without division by zero
        data = pd.Series([5.0, 5.0, 5.0, 5.0])
        z = compute_mad_zscore(data)
        assert (z == 0.0).all()

    def test_compute_provider_em_distribution(self):
        claims = pd.DataFrame([
            {"billing_provider_id": "P1", "cpt_code": "99214"},
            {"billing_provider_id": "P1", "cpt_code": "99215"},
            {"billing_provider_id": "P1", "cpt_code": "99213"},
        ])
        claims = extract_em_level(claims)
        dist = compute_provider_em_distribution(claims)

        assert dist.loc[0, "total_em_claims"] == 3
        assert dist.loc[0, "level_4_count"] == 1
        assert dist.loc[0, "level_5_count"] == 1
        assert dist.loc[0, "level_3_count"] == 1
        assert round(dist.loc[0, "level_45_share"], 2) == round(2 / 3, 2)

    def test_compute_provider_utilization_stats(self):
        claims = pd.DataFrame([
            {"billing_provider_id": "P1", "member_id": "M1"},
            {"billing_provider_id": "P1", "member_id": "M1"},
            {"billing_provider_id": "P1", "member_id": "M2"},
        ])
        stats = compute_provider_utilization_stats(claims)
        assert stats.loc[0, "total_claims"] == 3
        assert stats.loc[0, "unique_members"] == 2
        assert stats.loc[0, "visits_per_member"] == 1.5

    def test_add_claim_frequency(self):
        claims = pd.DataFrame([
            {"member_id": "M1", "billing_provider_id": "P1"},
            {"member_id": "M1", "billing_provider_id": "P1"},
            {"member_id": "M1", "billing_provider_id": "P2"},
        ])
        res = add_claim_frequency(claims)
        assert "claim_frequency" in res.columns
        assert res.loc[res["billing_provider_id"] == "P1", "claim_frequency"].iloc[0] == 2
        assert res.loc[res["billing_provider_id"] == "P2", "claim_frequency"].iloc[0] == 1

    def test_compute_member_utilization(self):
        claims = pd.DataFrame([
            {"member_id": "M1", "billing_provider_id": "P1", "cpt_code": "99213", "service_from": pd.Timestamp("2024-03-01")},
            {"member_id": "M1", "billing_provider_id": "P2", "cpt_code": "99214", "service_from": pd.Timestamp("2024-03-15")},
        ])
        stats = compute_member_utilization(claims, lookback_days=30, reference_date=pd.Timestamp("2024-03-20"))
        assert len(stats) == 1
        assert stats.loc[0, "total_claims"] == 2
        assert stats.loc[0, "unique_providers"] == 2
        assert stats.loc[0, "unique_cpts"] == 2
        assert stats.loc[0, "days_since_last_claim"] == 5

    def test_compute_peer_duration_stats(self):
        claims = pd.DataFrame([
            {"cpt_code": "99213", "service_minutes": 10},
            {"cpt_code": "99213", "service_minutes": 20},
            {"cpt_code": "99213", "service_minutes": 30},
        ])
        res = compute_peer_duration_stats(claims)
        assert len(res) == 1
        assert res.loc[0, "cpt_code"] == "99213"
        assert res.loc[0, "duration_median"] == 20

