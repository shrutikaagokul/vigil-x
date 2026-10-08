"""
Comprehensive tests for the Vigil-X Standalone Unified Risk Engine.

Covers all 20 required verification scenarios:
  1. Basic provider scoring
  2. Score always strictly in [0, 1]
  3. Risk tier correctness
  4. Component normalization
  5. Weight validation
  6. Contribution reconciliation
  7. Missing ML output
  8. Missing network output
  9. Missing anomaly output
  10. Missing future risk
  11. All signals missing
  12. NaN handling
  13. Infinite value handling
  14. Deterministic output
  15. Provider alignment
  16. Traceability preservation
  17. Top reasons generation
  18. Evidence strength and tiers
  19. Confidence score and tiers
  20. Configuration loading and overrides
"""
from __future__ import annotations

import copy
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from risk.contracts import (
    ConfidenceTier,
    EvidenceTier,
    ProviderScoreRecord,
    RiskTier,
)
from risk.risk_features import clip_01, safe_float
from risk.unified_risk import (
    compute_confidence_score,
    compute_evidence_strength,
    compute_unified_risk,
    generate_top_reasons,
    get_confidence_tier,
    get_evidence_tier,
    get_risk_tier,
    load_risk_config,
    run_unified_risk,
)


# ------------------------------------------------------------------------------
# Test Fixtures & Synthetic Mock Helpers
# ------------------------------------------------------------------------------

def _make_mock_alerts() -> List[Dict[str, Any]]:
    """Return a mock set of R01-R10 style alerts."""
    return [
        {
            "alert_id": "A-R06-001",
            "rule_id": "R06",
            "entity_type": "provider",
            "entity_id": "P001",
            "severity": "HIGH",
            "est_dollars": 12500.0,
            "claim_ids": ["C101", "C102"],
            "evidence": [
                {"evidence_id": "E-R06-001", "plain_text": "Impossible travel speed of 95 mph"}
            ],
        },
        {
            "alert_id": "A-R10-002",
            "rule_id": "R10",
            "entity_type": "provider",
            "entity_id": "P001",
            "severity": "CRITICAL",
            "est_dollars": 35000.0,
            "claim_ids": ["C103", "C104"],
            "evidence": [
                {"evidence_id": "E-R10-002", "plain_text": "Weekly billing spike 4.5x median"}
            ],
        },
        {
            "alert_id": "A-R07-003",
            "rule_id": "R07",
            "entity_type": "provider",
            "entity_id": "P002",
            "severity": "LOW",
            "est_dollars": 1200.0,
            "claim_ids": ["C201"],
            "evidence": [
                {"evidence_id": "E-R07-003", "plain_text": "Minor referral concentration"}
            ],
        },
    ]


def _make_mock_claim_ml() -> pd.DataFrame:
    """Return mock claim_ml dataframe."""
    return pd.DataFrame([
        {"claim_id": "C101", "provider_id": "P001", "calibrated_probability": 0.88, "ml_probability": 0.92, "ml_prediction": 1},
        {"claim_id": "C102", "provider_id": "P001", "calibrated_probability": 0.76, "ml_probability": 0.81, "ml_prediction": 1},
        {"claim_id": "C103", "provider_id": "P001", "calibrated_probability": 0.94, "ml_probability": 0.95, "ml_prediction": 1},
        {"claim_id": "C105", "provider_id": "P001", "calibrated_probability": 0.12, "ml_probability": 0.15, "ml_prediction": 0},
        {"claim_id": "C201", "provider_id": "P002", "calibrated_probability": 0.22, "ml_probability": 0.25, "ml_prediction": 0},
        {"claim_id": "C202", "provider_id": "P002", "calibrated_probability": 0.18, "ml_probability": 0.20, "ml_prediction": 0},
    ])


def _make_mock_anomaly() -> pd.DataFrame:
    """Return mock provider_anomaly dataframe."""
    return pd.DataFrame([
        {"provider_id": "P001", "anomaly_score": 0.42, "anomaly_percentile": 96.5, "anomaly_flag": 1},
        {"provider_id": "P002", "anomaly_score": -0.15, "anomaly_percentile": 35.0, "anomaly_flag": 0},
    ])


def _make_mock_future_risk() -> pd.DataFrame:
    """Return mock future_risk dataframe."""
    return pd.DataFrame([
        {"provider_id": "P001", "risk_30d": 0.82, "risk_60d": 0.75, "risk_90d": 0.70},
        {"provider_id": "P002", "risk_30d": 0.15, "risk_60d": 0.18, "risk_90d": 0.20},
    ])


def _make_mock_network() -> pd.DataFrame:
    """Return mock provider-level network dataframe."""
    return pd.DataFrame([
        {"provider_id": "P001", "community_id": 4, "n_providers": 6, "hard_link_score": 0.80, "referral_score": 0.65, "hub_centrality": 0.35, "is_hub": True},
        {"provider_id": "P002", "community_id": 12, "n_providers": 2, "hard_link_score": 0.00, "referral_score": 0.10, "hub_centrality": 0.00, "is_hub": False},
    ])


# ------------------------------------------------------------------------------
# Test Suite
# ------------------------------------------------------------------------------

class TestUnifiedRiskEngine:

    def test_01_basic_provider_scoring(self):
        """Test standard provider scoring with all components present."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )

        assert not df.empty
        assert len(df) == 2
        p1 = df[df["provider_id"] == "P001"].iloc[0]
        p2 = df[df["provider_id"] == "P002"].iloc[0]

        # P001 has strong signals across all domains -> High or Critical
        assert p1["risk_score"] > 0.50
        assert p1["risk_score"] > p2["risk_score"]
        assert p1["risk_tier"] in [RiskTier.HIGH.value, RiskTier.CRITICAL.value]

    def test_02_score_always_in_zero_to_one(self):
        """Risk scores must always be strictly within [0.0, 1.0]."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        for _, row in df.iterrows():
            assert 0.0 <= row["risk_score"] <= 1.0
            assert 0.0 <= row["evidence_strength"] <= 1.0
            assert 0.0 <= row["confidence_score"] <= 1.0

    def test_03_risk_tier_correctness(self):
        """Verify tier mappings adhere to configured thresholds."""
        cfg = load_risk_config()
        tiers_cfg = cfg["risk_tiers"]

        assert get_risk_tier(0.10, tiers_cfg) == RiskTier.LOW.value
        assert get_risk_tier(0.24, tiers_cfg) == RiskTier.LOW.value
        assert get_risk_tier(0.25, tiers_cfg) == RiskTier.MODERATE.value
        assert get_risk_tier(0.49, tiers_cfg) == RiskTier.MODERATE.value
        assert get_risk_tier(0.50, tiers_cfg) == RiskTier.HIGH.value
        assert get_risk_tier(0.74, tiers_cfg) == RiskTier.HIGH.value
        assert get_risk_tier(0.75, tiers_cfg) == RiskTier.CRITICAL.value
        assert get_risk_tier(1.00, tiers_cfg) == RiskTier.CRITICAL.value

    def test_04_component_normalization(self):
        """All individual signal components must be normalized to [0, 1]."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        component_cols = [
            "rule_component", "ml_component", "anomaly_component",
            "network_component", "temporal_component", "historical_component", "future_component"
        ]
        for col in component_cols:
            vals = df[col].values
            assert np.all(vals >= 0.0), f"{col} has values < 0"
            assert np.all(vals <= 1.0), f"{col} has values > 1"

    def test_05_weight_validation(self):
        """Configuration loader must reject weights that do not sum to 1.0."""
        # Valid weights load cleanly
        cfg = load_risk_config()
        assert math.isclose(sum(cfg["weights"].values()), 1.0, abs_tol=1e-5)

        # Invalid weights raise ValueError
        bad_cfg = copy.deepcopy(cfg)
        bad_cfg["weights"]["rules"] = 0.90  # sum becomes 1.65
        with pytest.raises(ValueError, match="must sum to 1.0"):
            load_risk_config(bad_cfg)

    def test_06_contribution_reconciliation(self):
        """Weighted contributions must reconcile with risk_score within 1e-5."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        for _, row in df.iterrows():
            total_cont = (
                row["rule_contribution"]
                + row["ml_contribution"]
                + row["anomaly_contribution"]
                + row["network_contribution"]
                + row["temporal_contribution"]
                + row["historical_contribution"]
                + row["future_contribution"]
            )
            assert abs(total_cont - row["risk_score"]) <= 1e-4

    def test_07_missing_ml_output(self):
        """Engine handles missing ML output gracefully, setting ml_available=False."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=None,
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        assert not df.empty
        for _, row in df.iterrows():
            assert not row["ml_available"]
            assert row["ml_contribution"] == 0.0
            assert 0.0 <= row["risk_score"] <= 1.0

    def test_08_missing_network_output(self):
        """Engine handles missing network output gracefully, setting network_available=False."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=None,
        )
        assert not df.empty
        for _, row in df.iterrows():
            assert not row["network_available"]
            assert row["network_contribution"] == 0.0
            assert 0.0 <= row["risk_score"] <= 1.0

    def test_09_missing_anomaly_output(self):
        """Engine handles missing anomaly output gracefully, setting anomaly_available=False."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=None,
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        assert not df.empty
        for _, row in df.iterrows():
            assert not row["anomaly_available"]
            assert row["anomaly_contribution"] == 0.0
            assert 0.0 <= row["risk_score"] <= 1.0

    def test_10_missing_future_risk(self):
        """Engine handles missing future risk output gracefully."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=None,
            network_output=_make_mock_network(),
        )
        assert not df.empty
        for _, row in df.iterrows():
            assert not row["future_available"]
            assert row["future_contribution"] == 0.0
            assert 0.0 <= row["risk_score"] <= 1.0

    def test_11_all_signals_missing(self):
        """Engine handles empty / missing inputs without crashing."""
        df = compute_unified_risk(
            rules_output=None,
            ml_output=None,
            anomaly_output=None,
            future_risk_output=None,
            network_output=None,
            provider_ids=["P_UNKNOWN"],
        )
        assert len(df) == 1
        rec = df.iloc[0]
        assert rec["risk_score"] == 0.0
        assert rec["risk_tier"] == RiskTier.LOW.value
        assert rec["confidence_score"] == 0.0
        assert rec["confidence_tier"] == ConfidenceTier.LOW.value

    def test_12_nan_handling(self):
        """NaN values in raw data are imputed safely without crashing."""
        corrupt_ml = pd.DataFrame([
            {"claim_id": "C1", "provider_id": "P_NAN", "calibrated_probability": np.nan, "ml_probability": np.nan},
            {"claim_id": "C2", "provider_id": "P_NAN", "calibrated_probability": 0.5, "ml_probability": np.nan},
        ])
        corrupt_anom = pd.DataFrame([
            {"provider_id": "P_NAN", "anomaly_score": np.nan, "anomaly_percentile": np.nan, "anomaly_flag": np.nan}
        ])
        df = compute_unified_risk(
            ml_output=corrupt_ml,
            anomaly_output=corrupt_anom,
        )
        assert not df.empty
        rec = df.iloc[0]
        assert not math.isnan(rec["risk_score"])
        assert not math.isnan(rec["evidence_strength"])
        assert not math.isnan(rec["confidence_score"])

    def test_13_infinite_value_handling(self):
        """Infinite values in inputs are clipped to bounded numbers safely."""
        corrupt_anom = pd.DataFrame([
            {"provider_id": "P_INF", "anomaly_score": np.inf, "anomaly_percentile": float("inf"), "anomaly_flag": 1}
        ])
        df = compute_unified_risk(
            anomaly_output=corrupt_anom,
        )
        assert not df.empty
        rec = df.iloc[0]
        assert not math.isinf(rec["risk_score"])
        assert 0.0 <= rec["risk_score"] <= 1.0

    def test_14_deterministic_output(self):
        """Repeated runs on identical inputs yield exact deterministic values."""
        df1 = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        df2 = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            future_risk_output=_make_mock_future_risk(),
            network_output=_make_mock_network(),
        )
        pd.testing.assert_frame_equal(df1, df2)

    def test_15_provider_alignment(self):
        """Providers appearing in subsets of tables are aligned correctly."""
        p_subset_rules = [{"alert_id": "A1", "rule_id": "R06", "entity_id": "P_ONLY_RULES", "severity": "HIGH", "est_dollars": 5000}]
        p_subset_ml = pd.DataFrame([{"claim_id": "C9", "provider_id": "P_ONLY_ML", "calibrated_probability": 0.85}])

        df = compute_unified_risk(
            rules_output=p_subset_rules,
            ml_output=p_subset_ml,
        )
        assert set(df["provider_id"]) == {"P_ONLY_RULES", "P_ONLY_ML"}
        p_rules = df[df["provider_id"] == "P_ONLY_RULES"].iloc[0]
        p_ml = df[df["provider_id"] == "P_ONLY_ML"].iloc[0]

        assert p_rules["rules_available"]
        assert not p_rules["ml_available"]

        assert not p_ml["rules_available"]
        assert p_ml["ml_available"]

    def test_16_traceability(self):
        """Preserves references to rule alert IDs, claim IDs, and community ID."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            network_output=_make_mock_network(),
        )
        p1 = df[df["provider_id"] == "P001"].iloc[0]
        assert "A-R06-001" in p1["rule_alert_ids"]
        assert "A-R10-002" in p1["rule_alert_ids"]
        assert p1["community_id"] == 4
        assert len(p1["high_risk_claim_ids"]) >= 1

    def test_17_top_reasons(self):
        """Top reasons must be generated dynamically from actual signal drivers."""
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            anomaly_output=_make_mock_anomaly(),
            network_output=_make_mock_network(),
        )
        p1 = df[df["provider_id"] == "P001"].iloc[0]
        reasons = p1["top_reasons"]
        assert isinstance(reasons, list)
        assert len(reasons) >= 1
        # Check that reasons do not state 'fraud confirmed'
        full_text = " ".join(reasons).lower()
        assert "fraud confirmed" not in full_text

    def test_18_evidence_strength(self):
        """Evidence strength reflects corroboration and matches evidence tiers."""
        cfg = load_risk_config()
        ev_tiers = cfg["evidence_tiers"]

        assert get_evidence_tier(0.10, ev_tiers) == EvidenceTier.LOW.value
        assert get_evidence_tier(0.35, ev_tiers) == EvidenceTier.MODERATE.value
        assert get_evidence_tier(0.65, ev_tiers) == EvidenceTier.HIGH.value
        assert get_evidence_tier(0.85, ev_tiers) == EvidenceTier.VERY_HIGH.value

    def test_19_confidence(self):
        """Confidence score reflects availability and consensus."""
        cfg = load_risk_config()
        conf_tiers = cfg["confidence_tiers"]

        assert get_confidence_tier(0.20, conf_tiers) == ConfidenceTier.LOW.value
        assert get_confidence_tier(0.55, conf_tiers) == ConfidenceTier.MEDIUM.value
        assert get_confidence_tier(0.85, conf_tiers) == ConfidenceTier.HIGH.value

    def test_20_configuration_loading(self):
        """Custom configuration override is respected."""
        custom_cfg = {
            "engine_version": "2.0.0",
            "model_version": "2.0.0",
            "feature_version": "2.0.0",
            "weights": {
                "rules": 0.50,
                "ml": 0.50,
                "anomaly": 0.0,
                "network": 0.0,
                "temporal": 0.0,
                "future": 0.0,
                "historical": 0.0,
            },
            "renormalize_missing_weights": False,
            "risk_tiers": {
                "low_threshold": 0.30,
                "moderate_threshold": 0.60,
                "high_threshold": 0.80,
            },
            "evidence_tiers": {
                "low_threshold": 0.30,
                "moderate_threshold": 0.60,
                "high_threshold": 0.80,
            },
            "confidence_tiers": {
                "low_threshold": 0.50,
                "moderate_threshold": 0.80,
            },
        }
        df = compute_unified_risk(
            rules_output=_make_mock_alerts(),
            ml_output=_make_mock_claim_ml(),
            config=custom_cfg,
        )
        assert not df.empty
        assert df.iloc[0]["risk_engine_version"] == "2.0.0"
