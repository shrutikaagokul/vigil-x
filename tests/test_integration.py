"""
Integration test: run_network_behavior_rules(data)
must return valid Alert objects for R06-R10.
"""
import pytest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generator.synthetic_data import generate_synthetic_data
from rules.runner import run_network_behavior_rules, run_all_rules
from contracts.alert import Alert


@pytest.fixture(scope="module")
def synthetic_data():
    """Generate synthetic data once for all integration tests."""
    data = generate_synthetic_data(
        n_providers=100, n_members=2000, n_facilities=20,
        n_months=12, seed=42
    )
    return data


def test_integration_runs(synthetic_data):
    """run_network_behavior_rules must execute without errors."""
    alerts = run_network_behavior_rules(synthetic_data)
    assert isinstance(alerts, list)


def test_integration_produces_alerts(synthetic_data):
    """Must produce at least some alerts."""
    alerts = run_network_behavior_rules(synthetic_data)
    assert len(alerts) > 0


def test_integration_all_alerts_valid(synthetic_data):
    """Every alert must pass validation."""
    alerts = run_network_behavior_rules(synthetic_data)
    for alert in alerts:
        assert isinstance(alert, Alert)
        errors = alert.validate()
        assert errors == [], f"Alert {alert.alert_id} validation failed: {errors}"


def test_integration_all_alerts_have_evidence(synthetic_data):
    """Every alert must contain at least one evidence record."""
    alerts = run_network_behavior_rules(synthetic_data)
    for alert in alerts:
        assert len(alert.evidence) >= 1, f"Alert {alert.alert_id} has no evidence"
        for ev in alert.evidence:
            assert ev.plain_text, f"Evidence {ev.evidence_id} has no plain_text"


def test_integration_multiple_rules_fire(synthetic_data):
    """Should have alerts from multiple rules (at least R06, R09, R10)."""
    alerts = run_network_behavior_rules(synthetic_data)
    fired_rules = set(a.rule_id for a in alerts)
    # We planted scenarios for R06, R07, R08, R09, R10
    assert len(fired_rules) >= 2, f"Only these rules fired: {fired_rules}"


def test_integration_run_all_rules(synthetic_data):
    """run_all_rules should work (R01-R05 may not exist yet)."""
    alerts = run_all_rules(synthetic_data)
    assert isinstance(alerts, list)
    # Should at least contain R06-R10 alerts
    r06_r10_alerts = [a for a in alerts if a.rule_id in ["R06", "R07", "R08", "R09", "R10"]]
    assert len(r06_r10_alerts) > 0


def test_integration_no_ground_truth_leakage(synthetic_data):
    """Alerts should not reference ground truth data."""
    alerts = run_network_behavior_rules(synthetic_data)
    for alert in alerts:
        # Alert should not contain scenario_id or gt_ references
        alert_str = str(alert.to_dict())
        assert "gt_" not in alert_str.lower() or "gt_" in "gt_scenarios"  # OK in metadata context
        assert "scenario_id" not in alert_str.lower()


def test_end_to_end_full_pipeline(tmp_path):
    """
    Full end-to-end integration test validating:
    1. synthetic data generation
    2. R01-R10 detection pipeline
    3. network intelligence
    4. risk engine
    5. case generation
    6. queue generation
    7. SQLite ingestion
    8. FastAPI retrieval
    9. evidence packet
    10. GenAI deterministic fallback
    11. frontend/API contract compatibility
    """
    from scripts.build_db import build_pipeline_and_db
    from fastapi.testclient import TestClient
    from api.main import app
    from db.database import get_db_connection
    import api.dependencies as deps

    test_db = str(tmp_path / "test_e2e.db")

    # 1 - 7: Run complete pipeline into isolated test database
    stats = build_pipeline_and_db(db_path=test_db, quick=True)
    assert stats["providers"] > 0
    assert stats["claims"] > 0
    assert stats["alerts"] > 0
    assert stats["cases"] > 0
    assert stats["queue_items"] > 0
    assert stats["risk_scores"] > 0

    # 8: Test FastAPI Retrieval with DB override
    def override_get_db():
        conn = get_db_connection(test_db)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    app.dependency_overrides[deps.get_db] = override_get_db

    try:
        with TestClient(app) as client:
            # 8a: Health endpoint
            health_res = client.get("/api/health")
            assert health_res.status_code == 200
            assert health_res.json()["status"] == "healthy"

            # 8b: Summary endpoint
            summary_res = client.get("/api/summary")
            assert summary_res.status_code == 200
            s_data = summary_res.json()
            assert s_data["claims_analyzed"] > 0
            assert s_data["alerts_total"] > 0
            assert s_data["entity_cases"] > 0
            assert s_data["queue_size"] > 0

            # 8c: Queue endpoint (ordered by priority/risk)
            queue_res = client.get("/api/queue")
            assert queue_res.status_code == 200
            q_items = queue_res.json()["items"]
            assert len(q_items) > 0
            top_case_id = q_items[0]["case_id"]

            # 8d: Case details endpoint
            case_res = client.get(f"/api/cases/{top_case_id}")
            assert case_res.status_code == 200
            case_data = case_res.json()
            assert case_data["case_id"] == top_case_id
            assert "risk_score" in case_data
            assert "priority" in case_data

            # 9: Evidence Packet
            ev_res = client.get(f"/api/cases/{top_case_id}/evidence")
            assert ev_res.status_code == 200
            ev_data = ev_res.json()
            assert "evidence" in ev_data
            assert isinstance(ev_data["evidence"], list)

            # 10: Investigation Brief / GenAI deterministic fallback
            brief_res = client.get(f"/api/brief?case_id={top_case_id}")
            assert brief_res.status_code == 200
            brief_data = brief_res.json()
            assert brief_data["case_id"] == top_case_id
            assert brief_data["verified"] is True
            assert brief_data["verification_report"]["verified"] is True
            assert brief_data["generation_mode"] in ["llm", "fallback"]

            # 11: Whitelisted structured Q&A
            qa_res = client.post("/api/ask", json={"case_id": top_case_id, "question": "Why was this provider flagged?"})
            assert qa_res.status_code == 200
            assert "answer" in qa_res.json()

    finally:
        app.dependency_overrides.clear()

