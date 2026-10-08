"""
Unit tests for the SIU Priority Engine, signal derivations, weight renormalization,
and deterministic explanation generation.
"""
import math
import pytest
from cases.contracts import InvestigationCase
from siu.priority_engine import (
    compute_case_signals,
    compute_priority_score,
    derive_anomaly_signal,
    derive_behavioral_signal,
    derive_evidence_signal,
    derive_exposure_signal,
    derive_future_risk_signal,
    derive_network_signal,
    derive_risk_signal,
    determine_priority_tier,
    generate_priority_reasons,
    load_queue_config,
)


def _make_sample_case(**overrides) -> dict:
    defaults = {
        "case_id": "CASE-000001",
        "provider_id": "P0030",
        "risk_score": 0.454,
        "risk_tier": "MODERATE",
        "evidence_strength": 0.745,
        "confidence_score": 0.806,
        "estimated_exposure": 84737.50,
        "community_id": 3,
        "network_relationships": [{"provider_id": "P0012", "strength": 0.85}],
        "anomaly_score": 0.334,
        "anomaly_flag": 1,
        "risk_30d": 0.002,
        "risk_60d": 0.116,
        "risk_90d": 0.028,
        "claim_count": 109,
        "high_risk_claim_count": 109,
        "rule_alert_count": 7,
        "high_severity_rule_count": 2,
        "distinct_rule_count": 3,
        "status": "NEW",
        "priority": "MEDIUM",
    }
    defaults.update(overrides)
    return defaults


class TestPriorityEngine:
    """Test suite for priority scoring engine and signal derivations."""

    def test_01_config_loading_and_weights(self):
        cfg = load_queue_config()
        weights = cfg["siu"]["weights"]
        assert abs(sum(weights.values()) - 1.0) < 1e-4

        # Bad weights fail validation
        bad_cfg = {"siu": {"weights": {"risk_score": 0.5}}}
        with pytest.raises(ValueError, match="must sum to 1.0"):
            load_queue_config(bad_cfg)

    def test_02_risk_and_evidence_derivation(self):
        case = _make_sample_case()
        r_sig, r_act = derive_risk_signal(case)
        assert r_act is True
        assert r_sig == 0.454

        e_sig, e_act = derive_evidence_signal(case)
        assert e_act is True
        assert e_sig == 0.745

        # Missing risk
        case_no_risk = _make_sample_case(risk_score=None)
        r_sig_none, r_act_none = derive_risk_signal(case_no_risk)
        assert r_act_none is False
        assert r_sig_none == 0.0

    def test_03_exposure_normalization(self):
        log_min = math.log1p(0.0)
        log_max = math.log1p(100000.0)

        # Zero exposure
        exp_0 = derive_exposure_signal(0.0, log_min, log_max)
        assert exp_0 == 0.0

        # Maximum exposure
        exp_max = derive_exposure_signal(100000.0, log_min, log_max)
        assert abs(exp_max - 1.0) < 1e-4

        # Moderate exposure
        exp_mid = derive_exposure_signal(5000.0, log_min, log_max)
        assert 0.0 < exp_mid < 1.0

        # Enormous outlier does not break boundary [0, 1]
        exp_huge = derive_exposure_signal(10000000.0, log_min, log_max)
        assert exp_huge == 1.0

    def test_04_network_signal(self):
        case = _make_sample_case()
        sig, act = derive_network_signal(case)
        assert act is True
        assert 0.0 < sig <= 1.0

        # Missing network entirely
        case_no_net = _make_sample_case(community_id=None, network_relationships=[])
        sig_none, act_none = derive_network_signal(case_no_net)
        assert act_none is False
        assert sig_none == 0.0

    def test_05_anomaly_signal(self):
        case_flagged = _make_sample_case(anomaly_score=0.334, anomaly_flag=1)
        sig_f, act_f = derive_anomaly_signal(case_flagged)
        assert act_f is True
        assert sig_f >= 0.60

        case_inlier = _make_sample_case(anomaly_score=-0.05, anomaly_flag=0)
        sig_i, act_i = derive_anomaly_signal(case_inlier)
        assert act_i is True
        assert sig_i < 0.30

        # Missing anomaly
        case_none = _make_sample_case(anomaly_score=None, anomaly_flag=None)
        sig_n, act_n = derive_anomaly_signal(case_none)
        assert act_n is False
        assert sig_n == 0.0

    def test_06_future_risk_signal(self):
        case = _make_sample_case(risk_30d=0.01, risk_60d=0.116, risk_90d=0.05)
        sig, act = derive_future_risk_signal(case)
        assert act is True
        assert sig == 0.116  # Max across horizons

        case_missing = _make_sample_case(risk_30d=None, risk_60d=None, risk_90d=None)
        sig_m, act_m = derive_future_risk_signal(case_missing)
        assert act_m is False
        assert sig_m == 0.0

    def test_07_behavioral_signal(self):
        case = _make_sample_case(claim_count=100, high_risk_claim_count=50, rule_alert_count=5, distinct_rule_count=3)
        sig, act = derive_behavioral_signal(case)
        assert act is True
        assert 0.0 < sig <= 1.0

        case_zero = _make_sample_case(claim_count=0, rule_alert_count=0)
        sig_z, act_z = derive_behavioral_signal(case_zero)
        assert act_z is False
        assert sig_z == 0.0

    def test_08_weight_renormalization_on_missing_signals(self):
        # Case with missing future risk and missing network
        case = _make_sample_case(
            community_id=None,
            network_relationships=[],
            risk_30d=None,
            risk_60d=None,
            risk_90d=None,
        )
        signals, active = compute_case_signals(case)
        assert "network_signal" not in active
        assert "future_risk_signal" not in active

        score = compute_priority_score(case)
        assert 0.0 <= score <= 1.0

    def test_09_priority_tier_mapping(self):
        thresholds = {"critical": 0.80, "high": 0.60, "medium": 0.35}
        assert determine_priority_tier(0.85, thresholds) == "CRITICAL"
        assert determine_priority_tier(0.65, thresholds) == "HIGH"
        assert determine_priority_tier(0.40, thresholds) == "MEDIUM"
        assert determine_priority_tier(0.20, thresholds) == "LOW"

    def test_10_deterministic_scoring(self):
        case = _make_sample_case()
        s1 = compute_priority_score(case)
        s2 = compute_priority_score(case)
        assert s1 == s2

    def test_11_priority_reasons_defensive_language(self):
        case = _make_sample_case()
        signals, _ = compute_case_signals(case)
        reasons = generate_priority_reasons(case, signals)
        assert len(reasons) >= 1
        assert len(reasons) <= 5

        # Check no prohibited words in reasons
        for r in reasons:
            for term in ["fraud confirmed", "fraudster", "guilty", "committed fraud"]:
                assert term not in r.lower()
