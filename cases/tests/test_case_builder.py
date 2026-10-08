"""
Comprehensive tests for the Vigil-X Standalone Case Builder Subsystem.

Covers all 25 required test scenarios:
  1. one provider → one case
  2. multiple alerts → one consolidated case
  3. duplicate claims are deduplicated
  4. duplicate alerts are deduplicated
  5. case IDs deterministic
  6. provider IDs deterministic
  7. risk fields copied correctly
  8. evidence strength copied correctly
  9. confidence copied correctly
  10. estimated exposure
  11. priority mapping
  12. status defaults to NEW
  13. missing ML
  14. missing network
  15. missing anomaly
  16. missing future risk
  17. missing rules
  18. no duplicate provider cases
  19. eligibility threshold
  20. top reasons preserved
  21. traceability preserved
  22. summary contains no prohibited fraud-confirmation language
  23. recommendations are deterministic
  24. output schema
  25. same input produces identical output
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from cases.contracts import (
    CaseEvidenceRecord,
    CasePriority,
    CaseStatus,
    InvestigationCase,
)
from cases.case_builder import (
    build_cases,
    generate_case_id,
    generate_case_summary,
    generate_case_title,
    generate_investigation_recommendations,
    is_provider_eligible,
    load_case_config,
    run_case_builder,
)


# ------------------------------------------------------------------------------
# Mock Data Fixtures
# ------------------------------------------------------------------------------

def _make_mock_provider_scores() -> pd.DataFrame:
    """Return mock provider_scores DataFrame matching Unified Risk Engine schema."""
    return pd.DataFrame([
        {
            "provider_id": "P0030",
            "risk_score": 0.454,
            "risk_tier": "MODERATE",
            "evidence_strength": 0.745,
            "evidence_tier": "HIGH",
            "confidence_score": 0.806,
            "confidence_tier": "HIGH",
            "rule_component": 0.516,
            "ml_component": 0.432,
            "anomaly_component": 1.0,
            "network_component": 0.20,
            "temporal_component": 0.0,
            "historical_component": 0.0,
            "future_component": 0.042,
            "estimated_rule_dollars": 84737.50,
            "high_risk_claim_count": 109,
            "rule_alert_count": 7,
            "high_severity_rule_count": 2,
            "anomaly_score": 0.334,
            "anomaly_flag": 1,
            "risk_30d": 0.002,
            "risk_60d": 0.116,
            "risk_90d": 0.028,
            "community_id": 3,
            "top_reasons": ["Multiple billing rule anomalies", "100th percentile behavioral anomaly"],
            "high_risk_claim_ids": ["C101", "C102", "C103"],
            "rule_alert_ids": ["A-R06-001", "A-R10-002"],
            "evidence_ids": ["E-R06-001", "E-R10-002"],
            "rules_available": True,
            "ml_available": True,
            "anomaly_available": True,
            "network_available": True,
            "future_available": True,
        },
        {
            "provider_id": "P0011",
            "risk_score": 0.347,
            "risk_tier": "MODERATE",
            "evidence_strength": 0.453,
            "evidence_tier": "MODERATE",
            "confidence_score": 0.789,
            "confidence_tier": "HIGH",
            "rule_component": 0.184,
            "ml_component": 0.488,
            "anomaly_component": 0.995,
            "network_component": 0.04,
            "temporal_component": 0.0,
            "historical_component": 0.0,
            "future_component": 0.042,
            "estimated_rule_dollars": 12000.0,
            "high_risk_claim_count": 50,
            "rule_alert_count": 2,
            "high_severity_rule_count": 0,
            "anomaly_score": 0.141,
            "anomaly_flag": 1,
            "risk_30d": 0.002,
            "risk_60d": 0.116,
            "risk_90d": 0.028,
            "community_id": 6,
            "top_reasons": ["Referral network anomaly", "Behavioral billing anomaly"],
            "high_risk_claim_ids": ["C201", "C202"],
            "rule_alert_ids": ["A-R07-001"],
            "evidence_ids": ["E-R07-001"],
            "rules_available": True,
            "ml_available": True,
            "anomaly_available": True,
            "network_available": True,
            "future_available": True,
        },
        {
            "provider_id": "P_LOW_01",
            "risk_score": 0.08,
            "risk_tier": "LOW",
            "evidence_strength": 0.12,
            "evidence_tier": "LOW",
            "confidence_score": 0.85,
            "confidence_tier": "HIGH",
            "rule_component": 0.0,
            "ml_component": 0.0,
            "anomaly_component": 0.10,
            "network_component": 0.0,
            "temporal_component": 0.0,
            "historical_component": 0.0,
            "future_component": 0.0,
            "estimated_rule_dollars": 0.0,
            "high_risk_claim_count": 0,
            "rule_alert_count": 0,
            "high_severity_rule_count": 0,
            "anomaly_score": -0.3,
            "anomaly_flag": 0,
            "risk_30d": 0.0,
            "risk_60d": 0.0,
            "risk_90d": 0.0,
            "community_id": None,
            "top_reasons": ["Baseline billing profile"],
            "high_risk_claim_ids": [],
            "rule_alert_ids": [],
            "evidence_ids": [],
            "rules_available": True,
            "ml_available": True,
            "anomaly_available": True,
            "network_available": True,
            "future_available": True,
        },
    ])


def _make_mock_alerts() -> List[Dict[str, Any]]:
    """Return mock alerts with multiple alerts for P0030."""
    return [
        {
            "alert_id": "A-R06-001",
            "rule_id": "R06",
            "entity_type": "provider",
            "entity_id": "P0030",
            "severity": "HIGH",
            "est_dollars": 25000.0,
            "claim_ids": ["C101", "C102"],
            "evidence": [{"evidence_id": "E-R06-001", "plain_text": "Impossible travel speed 90 mph"}],
        },
        {
            "alert_id": "A-R10-002",
            "rule_id": "R10",
            "entity_type": "provider",
            "entity_id": "P0030",
            "severity": "CRITICAL",
            "est_dollars": 59737.5,
            "claim_ids": ["C102", "C103"],  # C102 duplicated intentionally
            "evidence": [{"evidence_id": "E-R10-002", "plain_text": "Billing spike 4.8x median"}],
        },
    ]


# ------------------------------------------------------------------------------
# Test Suite
# ------------------------------------------------------------------------------

class TestCaseBuilder:

    def test_01_one_provider_one_case(self):
        """Each eligible provider must result in exactly one investigation case."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        # 2 eligible providers (P0030 and P0011); P_LOW_01 filtered by default eligibility
        assert len(cases_df) == 2
        assert cases_df["provider_id"].nunique() == 2
        assert set(cases_df["provider_id"]) == {"P0030", "P0011"}

    def test_02_multiple_alerts_consolidated(self):
        """Multiple alerts for the same provider are consolidated into a single case."""
        df_scores = _make_mock_provider_scores()
        alerts = _make_mock_alerts()
        cases_df, evidence_df = build_cases(df_scores, alerts=alerts)

        p30_case = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert p30_case["rule_alert_count"] >= 2
        assert "A-R06-001" in p30_case["alert_ids"]
        assert "A-R10-002" in p30_case["alert_ids"]

    def test_03_duplicate_claims_deduplicated(self):
        """Claim IDs appearing in multiple alerts are deduplicated in the case."""
        df_scores = _make_mock_provider_scores()
        alerts = _make_mock_alerts()  # Alert 1 and 2 both contain C102
        cases_df, _ = build_cases(df_scores, alerts=alerts)

        p30_case = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        claims = p30_case["claim_ids"]
        assert len(claims) == len(set(claims)), "Duplicate claim IDs found in case"
        assert "C102" in claims

    def test_04_duplicate_alerts_deduplicated(self):
        """Repeated alert IDs are deduplicated in the case."""
        df_scores = _make_mock_provider_scores()
        alerts = _make_mock_alerts() + _make_mock_alerts()  # Duplicate alert list
        cases_df, _ = build_cases(df_scores, alerts=alerts)

        p30_case = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        alert_ids = p30_case["alert_ids"]
        assert len(alert_ids) == len(set(alert_ids)), "Duplicate alert IDs found in case"

    def test_05_case_ids_deterministic(self):
        """Case IDs are deterministic (e.g. CASE-000001) across repeated executions."""
        df_scores = _make_mock_provider_scores()
        cases_1, _ = build_cases(df_scores)
        cases_2, _ = build_cases(df_scores)

        assert cases_1["case_id"].tolist() == cases_2["case_id"].tolist()
        assert cases_1["case_id"].iloc[0] == "CASE-000001"
        assert cases_1["case_id"].iloc[1] == "CASE-000002"

    def test_06_provider_ids_deterministic(self):
        """Provider ordering is deterministic based on risk ranking."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        # P0030 (risk 0.454) ranks ahead of P0011 (risk 0.347)
        assert cases_df["provider_id"].iloc[0] == "P0030"
        assert cases_df["provider_id"].iloc[1] == "P0011"

    def test_07_risk_fields_copied_correctly(self):
        """Unified risk scores and tiers are copied exactly from provider_scores."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert math.isclose(p30["risk_score"], 0.454)
        assert p30["risk_tier"] == "MODERATE"

    def test_08_evidence_strength_copied_correctly(self):
        """Evidence strength and evidence tier are copied accurately."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert math.isclose(p30["evidence_strength"], 0.745)
        assert p30["evidence_tier"] == "HIGH"

    def test_09_confidence_copied_correctly(self):
        """Confidence score and confidence tier are copied accurately."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert math.isclose(p30["confidence_score"], 0.806)
        assert p30["confidence_tier"] == "HIGH"

    def test_10_estimated_exposure(self):
        """Estimated exposure is derived from available financial evidence."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert math.isclose(p30["estimated_exposure"], 84737.50)

    def test_11_priority_mapping(self):
        """Priority correctly maps from risk_tier (e.g. MODERATE -> MEDIUM, HIGH -> HIGH)."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        # MODERATE risk tier maps to MEDIUM priority
        assert p30["priority"] == CasePriority.MEDIUM.value

    def test_12_status_defaults_to_new(self):
        """Case status must default strictly to NEW."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        for _, case in cases_df.iterrows():
            assert case["status"] == CaseStatus.NEW.value
            assert case["status"] != "CONFIRMED_FRAUD"

    def test_13_missing_ml(self):
        """Case Builder handles missing ML outputs gracefully."""
        df_scores = _make_mock_provider_scores()
        df_scores["high_risk_claim_ids"] = None
        df_scores["high_risk_claim_count"] = 0
        cases_df, _ = build_cases(df_scores)

        assert not cases_df.empty
        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert p30["high_risk_claim_count"] == 0

    def test_14_missing_network(self):
        """Case Builder handles missing network output gracefully."""
        df_scores = _make_mock_provider_scores()
        df_scores["community_id"] = None
        cases_df, _ = build_cases(df_scores, network_output=None)

        assert not cases_df.empty
        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert p30["community_id"] is None
        assert p30["network_relationships"] == []

    def test_15_missing_anomaly(self):
        """Case Builder handles missing provider anomaly gracefully."""
        df_scores = _make_mock_provider_scores()
        df_scores["anomaly_score"] = None
        df_scores["anomaly_flag"] = None
        cases_df, _ = build_cases(df_scores)

        assert not cases_df.empty
        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert p30["anomaly_flag"] == 0

    def test_16_missing_future_risk(self):
        """Case Builder handles missing future risk gracefully."""
        df_scores = _make_mock_provider_scores()
        df_scores["risk_30d"] = None
        cases_df, _ = build_cases(df_scores)

        assert not cases_df.empty
        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert p30["risk_30d"] == 0.0

    def test_17_missing_rules(self):
        """Case Builder handles providers with zero rule alerts gracefully."""
        df_scores = _make_mock_provider_scores()
        df_scores["rule_alert_count"] = 0
        df_scores["rule_alert_ids"] = [[] for _ in range(len(df_scores))]
        cases_df, _ = build_cases(df_scores, alerts=None)

        assert not cases_df.empty
        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert p30["rule_alert_count"] == 0

    def test_18_no_duplicate_provider_cases(self):
        """Even if provider appears multiple times in input scores, only one case is created."""
        df_scores = _make_mock_provider_scores()
        # Duplicate row for P0030 intentionally
        df_dup = pd.concat([df_scores, df_scores[df_scores["provider_id"] == "P0030"]], ignore_index=True)
        cases_df, _ = build_cases(df_dup)

        assert len(cases_df) == 2
        assert len(cases_df[cases_df["provider_id"] == "P0030"]) == 1

    def test_19_eligibility_threshold(self):
        """Providers below the eligibility criteria are filtered out."""
        df_scores = _make_mock_provider_scores()
        custom_cfg = {
            "eligibility": {
                "min_risk_score": 0.40,
                "eligible_risk_tiers": ["MODERATE", "HIGH", "CRITICAL"],
                "min_evidence_strength": 0.70,
                "all_providers": False,
            }
        }
        cases_df, _ = build_cases(df_scores, config=custom_cfg)

        # Only P0030 has risk_score 0.454 >= 0.40; P0011 has 0.347 and is excluded
        assert len(cases_df) == 1
        assert cases_df.iloc[0]["provider_id"] == "P0030"

    def test_20_top_reasons_preserved(self):
        """Top reasons from Unified Risk Engine are preserved in the case."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert isinstance(p30["top_reasons"], list)
        assert len(p30["top_reasons"]) >= 1
        assert "Multiple billing rule anomalies" in p30["top_reasons"]

    def test_21_traceability_preserved(self):
        """Alert IDs, claim IDs, and evidence IDs remain traceable."""
        df_scores = _make_mock_provider_scores()
        alerts = _make_mock_alerts()
        cases_df, evidence_df = build_cases(df_scores, alerts=alerts)

        p30 = cases_df[cases_df["provider_id"] == "P0030"].iloc[0]
        assert "A-R06-001" in p30["alert_ids"]
        assert "C101" in p30["claim_ids"]

        # Check granular evidence table
        p30_ev = evidence_df[evidence_df["case_id"] == p30["case_id"]]
        assert not p30_ev.empty
        assert "A-R06-001" in p30_ev["evidence_id"].values

    def test_22_summary_defensive_language(self):
        """Case summaries must never contain prohibited fraud-accusation language."""
        df_scores = _make_mock_provider_scores()
        cases_df, _ = build_cases(df_scores)

        for _, case in cases_df.iterrows():
            text = (case["title"] + " " + case["summary"]).lower()
            assert "fraud confirmed" not in text
            assert "fraudster" not in text
            assert "committed fraud" not in text
            assert "guilty" not in text
            assert "prioritized for human investigation" in text

    def test_23_recommendations_are_deterministic(self):
        """Recommendations are deterministically derived from signals."""
        recs1 = generate_investigation_recommendations(["R06", "R10"], 5, 1, 0.4, 3, [])
        recs2 = generate_investigation_recommendations(["R06", "R10"], 5, 1, 0.4, 3, [])
        assert recs1 == recs2
        assert any("travel feasibility" in r.lower() for r in recs1)
        assert any("billing surge" in r.lower() for r in recs1)

    def test_24_output_schema(self):
        """Cases and Case Evidence tables conform strictly to required schemas."""
        df_scores = _make_mock_provider_scores()
        alerts = _make_mock_alerts()
        cases_df, evidence_df = build_cases(df_scores, alerts=alerts)

        required_case_cols = [
            "case_id", "provider_id", "title", "summary", "risk_score", "risk_tier",
            "evidence_strength", "evidence_tier", "confidence_score", "confidence_tier",
            "estimated_exposure", "status", "priority", "created_at", "updated_at",
            "community_id", "claim_count", "high_risk_claim_count", "rule_alert_count",
            "top_reasons", "claim_ids", "alert_ids", "investigation_recommendations"
        ]
        for col in required_case_cols:
            assert col in cases_df.columns, f"Missing case column {col}"

        required_ev_cols = [
            "case_id", "evidence_id", "source_type", "source_id", "provider_id", "description"
        ]
        for col in required_ev_cols:
            assert col in evidence_df.columns, f"Missing evidence column {col}"

    def test_25_same_input_produces_identical_output(self):
        """Repeated executions on identical inputs yield bit-exact outputs."""
        df_scores = _make_mock_provider_scores()
        alerts = _make_mock_alerts()
        cases_1, ev_1 = build_cases(df_scores, alerts=alerts)
        cases_2, ev_2 = build_cases(df_scores, alerts=alerts)

        # Ignore timestamps which vary by microsecond if freshly generated
        cases_1_cmp = cases_1.drop(columns=["created_at", "updated_at"])
        cases_2_cmp = cases_2.drop(columns=["created_at", "updated_at"])
        pd.testing.assert_frame_equal(cases_1_cmp, cases_2_cmp)
        pd.testing.assert_frame_equal(ev_1, ev_2)
