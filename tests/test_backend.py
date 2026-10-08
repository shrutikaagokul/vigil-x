"""
Backend API and Database Tests for Vigil-X.

Covers:
- Database initialization and loading
- API startup and health
- Summary metrics and funnel
- Queue sorting and capacity constraints
- Case details, evidence provenance, timeline, network
- Decisions, audit log, claims, providers, risk, evaluation
- Error handling (404 not found, 400 invalid params)
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.database import init_db, get_db_connection
from db.loader import rebuild_database
from contracts.investigation import CaseStatus


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with a populated test database."""
    test_db = "test_backend.db"
    # Ensure fresh test db
    init_db(test_db)
    # Load quick sample data
    from generator.synthetic_data import generate_synthetic_data
    from rules.runner import run_network_behavior_rules
    data = generate_synthetic_data(n_providers=20, n_members=200, n_facilities=5, n_months=6, seed=42)
    alerts = run_network_behavior_rules(data)
    rebuild_database(db_path=test_db, data_dict=data, alerts=alerts)

    # Override DB_PATH for test client
    import api.dependencies as deps
    orig_get_db = deps.get_db

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

    with TestClient(app) as test_client:
        yield test_client

    # Clean up override and test db
    app.dependency_overrides.clear()
    import os
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except OSError:
            pass


def test_api_root(client):
    """Root endpoint responds with service info."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "Vigil-X Investigation API"
    assert data["synthetic"] is True


def test_health_endpoint(client):
    """Health check confirms database readiness."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "ready"
    assert data["table_count"] > 10
    assert data["synthetic"] is True
    assert "as_of" in data


def test_summary_endpoint(client):
    """Summary returns counts, totals, and investigation funnel."""
    res = client.get("/api/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["claims_analyzed"] > 0
    assert data["paid_total"] >= 0
    assert data["alerts_total"] > 0
    assert data["queue_size"] > 0
    assert "funnel" in data
    assert data["funnel"]["cases_formed"] == data["entity_cases"]
    assert data["synthetic"] is True


def test_queue_sorting_and_capacity(client):
    """Queue endpoint supports sorting by priority and capacity limits."""
    # Default priority sort
    res = client.get("/api/queue")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0
    first_item = data["items"][0]
    assert "case_id" in first_item
    assert "ev_per_hour" in first_item

    # EV per hour sort
    res_ev = client.get("/api/queue?sort=ev_per_hour")
    assert res_ev.status_code == 200
    items_ev = res_ev.json()["items"]
    assert len(items_ev) > 0
    # First item should have highest ev_per_hour
    if len(items_ev) > 1:
        assert items_ev[0]["ev_per_hour"] >= items_ev[-1]["ev_per_hour"]

    # Capacity hours limit
    res_cap = client.get("/api/queue?capacity_hours=4.0")
    assert res_cap.status_code == 200
    assert len(res_cap.json()["items"]) <= len(data["items"])


def test_queue_invalid_sort(client):
    """Invalid sort parameter returns 400."""
    res = client.get("/api/queue?sort=invalid_sort_param")
    assert res.status_code == 400


def test_case_detail_and_provenance(client):
    """Case detail returns header, evidence ledger, timeline, and claims."""
    # Get first case from queue
    q_res = client.get("/api/queue")
    case_id = q_res.json()["items"][0]["case_id"]

    res = client.get(f"/api/cases/{case_id}")
    assert res.status_code == 200
    c_data = res.json()
    assert c_data["case_id"] == case_id
    assert c_data["risk_score"] > 0
    assert len(c_data["why_flagged"]) > 0
    assert "risk_components" in c_data

    # Case evidence ledger
    ev_res = client.get(f"/api/cases/{case_id}/evidence")
    assert ev_res.status_code == 200
    ev_data = ev_res.json()
    assert ev_data["total_evidence_items"] > 0
    first_ev = ev_data["evidence"][0]
    assert "rule_id" in first_ev
    assert "plain_text" in first_ev
    assert "source_table" in first_ev

    # Case timeline
    tl_res = client.get(f"/api/cases/{case_id}/timeline")
    assert tl_res.status_code == 200
    assert "timeline" in tl_res.json()

    # Case network
    net_res = client.get(f"/api/cases/{case_id}/network")
    assert net_res.status_code == 200
    assert "nodes" in net_res.json()["subgraph"]


def test_case_not_found(client):
    """Non-existent case ID returns 404."""
    res = client.get("/api/cases/CASE-DOES-NOT-EXIST")
    assert res.status_code == 404


def test_claims_and_providers_endpoints(client):
    """Claims and providers endpoints filter correctly."""
    # Claims
    res_claims = client.get("/api/claims?limit=10")
    assert res_claims.status_code == 200
    assert len(res_claims.json()["claims"]) > 0

    # Providers
    res_prov = client.get("/api/providers?limit=10")
    assert res_prov.status_code == 200
    assert len(res_prov.json()["providers"]) > 0
    pid = res_prov.json()["providers"][0]["provider_id"]

    # Single provider
    res_p1 = client.get(f"/api/providers/{pid}")
    assert res_p1.status_code == 200
    assert res_p1.json()["provider_id"] == pid


def test_decision_and_audit_flow(client):
    """Investigator decision updates case status and logs audit entry."""
    q_res = client.get("/api/queue")
    case_id = q_res.json()["items"][0]["case_id"]

    # Accept case
    res_dec = client.post("/api/decision", json={
        "case_id": case_id,
        "decision": "accept",
        "notes": "Verified billing anomaly; assigning to investigator",
        "actor": "siu_lead",
    })
    assert res_dec.status_code == 200
    dec_data = res_dec.json()
    assert dec_data["status"] == CaseStatus.ACCEPTED.value
    assert "audit_id" in dec_data

    # Verify updated status in case detail
    case_res = client.get(f"/api/cases/{case_id}")
    assert case_res.json()["status"] == CaseStatus.ACCEPTED.value

    # Verify audit log recorded
    audit_res = client.get(f"/api/audit?case_id={case_id}")
    assert audit_res.status_code == 200
    records = audit_res.json()["records"]
    assert any(r["decision"] == "accept" for r in records)


def test_evaluation_endpoint(client):
    """Evaluation endpoint returns stored benchmarks."""
    res = client.get("/api/evaluation")
    assert res.status_code == 200
    assert "evaluations" in res.json()
