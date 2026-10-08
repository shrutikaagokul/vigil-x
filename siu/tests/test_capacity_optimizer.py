"""
Unit tests for the SIU Capacity Optimizer, capacity-aware queue ranking,
baseline evaluations, and edge cases.
"""
import json
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from cases.contracts import CaseStatus, CasePriority
from siu.contracts import SIUQueueStatus
from siu.capacity_optimizer import (
    build_siu_queue,
    generate_evaluation_report,
    run_siu_pipeline,
)


def _make_mock_cases_df() -> pd.DataFrame:
    """Create a mock DataFrame with multiple cases for capacity testing."""
    records = [
        {
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
            "evidence_ids": ["E1", "E2"],
        },
        {
            "case_id": "CASE-000002",
            "provider_id": "P0011",
            "risk_score": 0.347,
            "risk_tier": "MODERATE",
            "evidence_strength": 0.453,
            "confidence_score": 0.789,
            "estimated_exposure": 12000.0,
            "community_id": 6,
            "network_relationships": [],
            "anomaly_score": 0.141,
            "anomaly_flag": 1,
            "risk_30d": 0.002,
            "risk_60d": 0.050,
            "risk_90d": 0.010,
            "claim_count": 50,
            "high_risk_claim_count": 20,
            "rule_alert_count": 3,
            "high_severity_rule_count": 0,
            "distinct_rule_count": 2,
            "status": "IN_REVIEW",
            "priority": "MEDIUM",
            "evidence_ids": ["E3"],
        },
        {
            "case_id": "CASE-000003",
            "provider_id": "P0099",
            "risk_score": 0.280,
            "risk_tier": "MODERATE",
            "evidence_strength": 0.600,
            "confidence_score": 0.750,
            "estimated_exposure": 5000.0,
            "community_id": 1,
            "network_relationships": [],
            "anomaly_score": -0.02,
            "anomaly_flag": 0,
            "risk_30d": 0.001,
            "risk_60d": 0.002,
            "risk_90d": 0.003,
            "claim_count": 30,
            "high_risk_claim_count": 5,
            "rule_alert_count": 2,
            "high_severity_rule_count": 0,
            "distinct_rule_count": 1,
            "status": "ESCALATED",
            "priority": "MEDIUM",
            "evidence_ids": ["E4"],
        },
        {
            "case_id": "CASE-000004",
            "provider_id": "P0088",
            "risk_score": 0.400,
            "risk_tier": "MODERATE",
            "evidence_strength": 0.700,
            "confidence_score": 0.800,
            "estimated_exposure": 20000.0,
            "community_id": 2,
            "network_relationships": [],
            "anomaly_score": 0.20,
            "anomaly_flag": 1,
            "risk_30d": 0.010,
            "risk_60d": 0.080,
            "risk_90d": 0.020,
            "claim_count": 40,
            "high_risk_claim_count": 15,
            "rule_alert_count": 4,
            "high_severity_rule_count": 1,
            "distinct_rule_count": 2,
            "status": "CLOSED",  # Should be excluded from active queue
            "priority": "MEDIUM",
            "evidence_ids": ["E5"],
        },
    ]
    return pd.DataFrame(records)


class TestCapacityOptimizer:
    """Test suite for capacity optimization, eligibility filtering, and report generation."""

    def test_01_eligibility_filtering_excludes_closed(self):
        df_cases = _make_mock_cases_df()
        queue_df, items = build_siu_queue(df_cases, daily_capacity=10)

        # CASE-000004 is CLOSED and should be excluded from active queue
        case_ids = queue_df["case_id"].tolist()
        assert "CASE-000004" not in case_ids
        assert len(queue_df) == 3
        assert len(items) == 3

    def test_02_capacity_selection_limits(self):
        df_cases = _make_mock_cases_df()
        # Daily capacity = 2 out of 3 eligible cases
        queue_df, items = build_siu_queue(df_cases, daily_capacity=2)

        selected = queue_df[queue_df["capacity_selected"] == True]
        deferred = queue_df[queue_df["capacity_selected"] == False]

        assert len(selected) == 2
        assert len(deferred) == 1

        assert selected.iloc[0]["capacity_rank"] == 1
        assert selected.iloc[0]["queue_status"] == SIUQueueStatus.QUEUED.value
        assert selected.iloc[1]["capacity_rank"] == 2
        assert selected.iloc[1]["queue_status"] == SIUQueueStatus.QUEUED.value

        assert deferred.iloc[0]["capacity_rank"] == 0
        assert deferred.iloc[0]["queue_status"] == SIUQueueStatus.DEFERRED.value

    def test_03_capacity_exceeds_eligible_cases(self):
        df_cases = _make_mock_cases_df()
        queue_df, _ = build_siu_queue(df_cases, daily_capacity=100)

        # All 3 eligible cases should be selected
        assert queue_df["capacity_selected"].all()
        assert (queue_df["capacity_rank"] > 0).all()

    def test_04_zero_capacity(self):
        df_cases = _make_mock_cases_df()
        queue_df, _ = build_siu_queue(df_cases, daily_capacity=0)

        # None selected
        assert not queue_df["capacity_selected"].any()
        assert (queue_df["capacity_rank"] == 0).all()
        assert (queue_df["queue_status"] == SIUQueueStatus.DEFERRED.value).all()

    def test_05_deterministic_tie_breaking(self):
        # Two cases with identical priority scores break tie by risk_score, then evidence, then exposure, then case_id
        df_ties = pd.DataFrame([
            {
                "case_id": "CASE-B",
                "provider_id": "P_B",
                "risk_score": 0.300,
                "risk_tier": "MODERATE",
                "evidence_strength": 0.500,
                "confidence_score": 0.800,
                "estimated_exposure": 1000.0,
                "community_id": None,
                "network_relationships": [],
                "anomaly_score": None,
                "anomaly_flag": None,
                "risk_30d": None,
                "risk_60d": None,
                "risk_90d": None,
                "claim_count": 10,
                "rule_alert_count": 1,
                "status": "NEW",
            },
            {
                "case_id": "CASE-A",
                "provider_id": "P_A",
                "risk_score": 0.300,
                "risk_tier": "MODERATE",
                "evidence_strength": 0.500,
                "confidence_score": 0.800,
                "estimated_exposure": 1000.0,
                "community_id": None,
                "network_relationships": [],
                "anomaly_score": None,
                "anomaly_flag": None,
                "risk_30d": None,
                "risk_60d": None,
                "risk_90d": None,
                "claim_count": 10,
                "rule_alert_count": 1,
                "status": "NEW",
            },
        ])
        queue_df, _ = build_siu_queue(df_ties, daily_capacity=2)
        # CASE-A should be ranked before CASE-B due to case_id ASC tie-breaker
        assert queue_df.iloc[0]["case_id"] == "CASE-A"
        assert queue_df.iloc[1]["case_id"] == "CASE-B"

    def test_06_queue_id_stability(self):
        df_cases = _make_mock_cases_df()
        q1, _ = build_siu_queue(df_cases, daily_capacity=2)
        q2, _ = build_siu_queue(df_cases, daily_capacity=2)

        assert q1["queue_id"].tolist() == q2["queue_id"].tolist()
        assert q1["case_id"].tolist() == q2["case_id"].tolist()
        assert q1["rank"].tolist() == [1, 2, 3]

    def test_07_evaluation_report_structure(self):
        df_cases = _make_mock_cases_df()
        queue_df, _ = build_siu_queue(df_cases, daily_capacity=2)
        report = generate_evaluation_report(df_cases, queue_df, daily_capacity=2)

        assert report["total_cases"] == 4
        assert report["eligible_cases"] == 3
        assert report["excluded_cases"] == 1
        assert report["selected_count"] == 2
        assert report["deferred_count"] == 1

        baselines = report["baseline_comparison_top_n"]
        assert "siu_unified_priority" in baselines
        assert "risk_only_baseline" in baselines
        assert "exposure_only_baseline" in baselines

        assert "Operational prioritization evaluation only" in report["evaluation_notes"]

    def test_08_empty_dataset_handling(self):
        empty_df = pd.DataFrame()
        queue_df, items = build_siu_queue(empty_df, daily_capacity=10)
        assert queue_df.empty
        assert items == []

        rep = generate_evaluation_report(empty_df, queue_df, daily_capacity=10)
        assert rep["total_cases"] == 0
        assert rep["eligible_cases"] == 0

    def test_09_single_case_dataset(self):
        single_df = _make_mock_cases_df().head(1)
        queue_df, items = build_siu_queue(single_df, daily_capacity=5)
        assert len(queue_df) == 1
        assert bool(queue_df.iloc[0]["capacity_selected"]) is True
        assert queue_df.iloc[0]["rank"] == 1

    def test_10_end_to_end_pipeline_run(self):
        df_cases = _make_mock_cases_df()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            cases_path = tmp_path / "cases.parquet"
            df_cases.to_parquet(cases_path, index=False)

            report = run_siu_pipeline(
                cases_input=cases_path,
                daily_capacity=2,
                output_dir=tmp_path / "siu",
            )

            assert (tmp_path / "siu" / "siu_queue.parquet").exists()
            assert (tmp_path / "siu" / "siu_queue.csv").exists()
            assert (tmp_path / "siu" / "siu_evaluation_report.json").exists()

            # Verify CSV JSON serialization
            df_csv = pd.read_csv(tmp_path / "siu" / "siu_queue.csv")
            assert isinstance(df_csv["priority_reasons"].iloc[0], str)
            reasons = json.loads(df_csv["priority_reasons"].iloc[0])
            assert isinstance(reasons, list)
