"""
Unit tests for SIU Priority Queue contracts and validation rules.
"""
import pytest
from siu.contracts import (
    SIUPriorityTier,
    SIUQueueItem,
    SIUQueueStatus,
)


def _make_valid_queue_item(**overrides) -> SIUQueueItem:
    defaults = {
        "queue_id": "SIU-000001",
        "case_id": "CASE-000001",
        "provider_id": "P0030",
        "rank": 1,
        "priority_score": 0.85,
        "priority_tier": SIUPriorityTier.CRITICAL.value,
        "risk_score": 0.454,
        "risk_tier": "MODERATE",
        "evidence_strength": 0.745,
        "confidence_score": 0.806,
        "estimated_exposure": 84737.50,
        "network_signal": 0.80,
        "anomaly_signal": 0.90,
        "future_risk_signal": 0.116,
        "behavioral_signal": 0.75,
        "case_status": "NEW",
        "queue_status": SIUQueueStatus.QUEUED.value,
        "capacity_selected": True,
        "capacity_rank": 1,
        "priority_reasons": ["High unified risk score (0.454)", "High supporting evidence strength (0.745)"],
        "claim_count": 109,
        "alert_count": 7,
        "evidence_count": 7,
        "community_id": 3,
        "created_at": "2026-10-08T18:00:00Z",
        "queued_at": "2026-10-08T18:05:00Z",
        "case_builder_version": "1.0.0",
        "siu_version": "1.0.0",
    }
    defaults.update(overrides)
    return SIUQueueItem(**defaults)


class TestSIUContracts:
    """Test suite verifying SIUQueueItem contract validations and integrity."""

    def test_01_valid_contract(self):
        item = _make_valid_queue_item()
        errors = item.validate()
        assert errors == []

    def test_02_missing_required_ids(self):
        item_no_qid = _make_valid_queue_item(queue_id="")
        assert "queue_id is required" in item_no_qid.validate()

        item_no_cid = _make_valid_queue_item(case_id="")
        assert "case_id is required" in item_no_cid.validate()

        item_no_pid = _make_valid_queue_item(provider_id="")
        assert "provider_id is required" in item_no_pid.validate()

    def test_03_priority_score_boundaries(self):
        item_low = _make_valid_queue_item(priority_score=-0.05)
        assert any("priority_score" in e for e in item_low.validate())

        item_high = _make_valid_queue_item(priority_score=1.05)
        assert any("priority_score" in e for e in item_high.validate())

    def test_04_signals_bounded_in_01(self):
        for sig in ["network_signal", "anomaly_signal", "future_risk_signal", "behavioral_signal", "risk_score", "evidence_strength"]:
            item_bad = _make_valid_queue_item(**{sig: 1.5})
            assert any(sig in e for e in item_bad.validate()), f"Expected {sig} to fail when > 1.0"

    def test_05_invalid_priority_tier(self):
        item = _make_valid_queue_item(priority_tier="SUPER_CRITICAL")
        assert any("invalid priority_tier" in e for e in item.validate())

    def test_06_invalid_queue_status(self):
        item = _make_valid_queue_item(queue_status="UNKNOWN_STATUS")
        assert any("invalid queue_status" in e for e in item.validate())

    def test_07_rank_and_capacity_rank_bounds(self):
        item_bad_rank = _make_valid_queue_item(rank=0)
        assert any("rank must be >= 1" in e for e in item_bad_rank.validate())

        item_bad_cap_rank = _make_valid_queue_item(capacity_rank=-1)
        assert any("capacity_rank must be >= 0" in e for e in item_bad_cap_rank.validate())

    def test_08_prohibited_fraud_language_rejected(self):
        prohibited_phrases = [
            "Provider is a confirmed fraudster",
            "SIU confirmed fraud on claim",
            "Found guilty of billing abuse",
            "Committed fraud on duplicate bills",
        ]
        for phrase in prohibited_phrases:
            item = _make_valid_queue_item(priority_reasons=[phrase])
            errs = item.validate()
            assert any("prohibited fraud-confirmation language" in e for e in errs), f"Failed to reject phrase: {phrase}"

    def test_09_to_dict_serialization(self):
        item = _make_valid_queue_item()
        d_raw = item.to_dict(serialize_lists=False)
        assert isinstance(d_raw["priority_reasons"], list)

        d_csv = item.to_dict(serialize_lists=True)
        assert isinstance(d_csv["priority_reasons"], str)
        assert "High unified risk score" in d_csv["priority_reasons"]
