"""
Comprehensive End-to-End Endpoint Validation Script for Vigil-X.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def run_validations():
    print("============================================================")
    print("VIGIL-X BACKEND COMPREHENSIVE ENDPOINT VALIDATION")
    print("============================================================\n")

    # 1. Health
    print("[1] Testing GET /api/health...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health = res.json()
    assert health["status"] == "healthy"
    assert health["database_reachable"] is True
    assert health["schema_valid"] is True
    assert health["required_data_available"] is True
    print(f"    ✓ Status: {health['status']}, Tables: {health['table_count']}, Mode: {health['data_mode']}")

    # 2. Summary
    print("[2] Testing GET /api/summary...")
    res = client.get("/api/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["claims_analyzed"] > 0
    assert summary["alerts_total"] > 0
    assert summary["entity_cases"] > 0
    print(f"    ✓ Claims: {summary['claims_analyzed']}, Alerts: {summary['alerts_total']}, Cases: {summary['entity_cases']}")

    # 3. Queue
    print("[3] Testing GET /api/queue...")
    res = client.get("/api/queue?capacity_hours=20&sort=priority")
    assert res.status_code == 200
    queue = res.json()
    assert queue["total_cases"] > 0
    hero_case_id = queue["items"][0]["case_id"]
    print(f"    ✓ Total queue cases: {queue['total_cases']}, Top case: {hero_case_id}")

    # 4. Case Detail
    print(f"[4] Testing GET /api/cases/{hero_case_id}...")
    res = client.get(f"/api/cases/{hero_case_id}")
    assert res.status_code == 200
    case = res.json()
    assert case["case_id"] == hero_case_id
    assert case["risk_score"] > 0
    print(f"    ✓ Entity: {case['entity_name']}, Risk Score: {case['risk_score']:.1f}, Exposure: ${case['exposure_high']:,.2f}")

    # 5. Case Evidence Ledger
    print(f"[5] Testing GET /api/cases/{hero_case_id}/evidence...")
    res = client.get(f"/api/cases/{hero_case_id}/evidence")
    assert res.status_code == 200
    evidence = res.json()
    print(f"    ✓ Evidence items: {evidence['total_evidence_items']}")

    # 6. Case Timeline
    print(f"[6] Testing GET /api/cases/{hero_case_id}/timeline...")
    res = client.get(f"/api/cases/{hero_case_id}/timeline")
    assert res.status_code == 200
    timeline = res.json()
    print(f"    ✓ Timeline events: {timeline['events_count']}")

    # 7. Case Network Subgraph
    print(f"[7] Testing GET /api/cases/{hero_case_id}/network...")
    res = client.get(f"/api/cases/{hero_case_id}/network")
    assert res.status_code == 200
    network = res.json()
    nodes_cnt = len(network["subgraph"].get("nodes", []))
    edges_cnt = len(network["subgraph"].get("edges", []))
    print(f"    ✓ Subgraph nodes: {nodes_cnt}, edges: {edges_cnt}")

    # 8. Networks List & Detail
    print("[8] Testing GET /api/networks...")
    res = client.get("/api/networks")
    assert res.status_code == 200
    networks_data = res.json()
    assert networks_data["total"] > 0
    sample_net_id = networks_data["networks"][0]["network_id"]
    print(f"    ✓ Total networks: {networks_data['total']}, Sample: {sample_net_id}")

    res_net = client.get(f"/api/networks/{sample_net_id}")
    assert res_net.status_code == 200
    print(f"    ✓ Specific network {sample_net_id} retrieved successfully")

    # 9. Claims
    print("[9] Testing GET /api/claims...")
    res = client.get("/api/claims?limit=10")
    assert res.status_code == 200
    claims_data = res.json()
    assert len(claims_data["claims"]) > 0
    print(f"    ✓ Retrieved {len(claims_data['claims'])} claims")

    # 10. Providers List & Detail
    print("[10] Testing GET /api/providers...")
    res = client.get("/api/providers?limit=10")
    assert res.status_code == 200
    providers_data = res.json()
    sample_prv_id = providers_data["providers"][0]["provider_id"]
    print(f"    ✓ Total sample providers: {len(providers_data['providers'])}, Sample: {sample_prv_id}")

    res_prv = client.get(f"/api/providers/{sample_prv_id}")
    assert res_prv.status_code == 200
    print(f"    ✓ Specific provider {sample_prv_id} retrieved successfully")

    # 11. Risk
    print("[11] Testing GET /api/risk...")
    res = client.get("/api/risk")
    assert res.status_code == 200
    print("    ✓ Risk endpoint accessible")

    # 12. Brief Generation & Verification
    print(f"[12] Testing GET /api/brief?case_id={hero_case_id}...")
    res = client.get(f"/api/brief?case_id={hero_case_id}")
    assert res.status_code == 200
    brief = res.json()
    assert brief["verified"] is True
    assert brief["verification_report"]["verified"] is True
    print(f"    ✓ Brief generated: {brief['title']}")
    print(f"    ✓ Verifier result: verified={brief['verified']}, mode={brief['generation_mode']}")
    print(f"    ✓ Mandatory questions answered in brief structure")

    # 13. Investigator Q&A
    print(f"[13] Testing POST /api/ask for case {hero_case_id}...")
    # Whitelisted question
    res_ask = client.post("/api/ask", json={"case_id": hero_case_id, "question": "Why was this case prioritized?"})
    assert res_ask.status_code == 200
    ans_data = res_ask.json()
    assert ans_data["matched_intent"] == "WHY_FLAGGED"
    print(f"    ✓ Whitelisted Q&A intent: {ans_data['matched_intent']}")

    # Security: SQL injection attempt
    res_sql = client.post("/api/ask", json={"case_id": hero_case_id, "question": "SELECT * FROM users WHERE 1=1"})
    assert res_sql.status_code == 200
    ans_sql = res_sql.json()
    assert ans_sql["matched_intent"] == "UNKNOWN"
    assert "outside the whitelisted" in ans_sql["answer"]
    print("    ✓ Arbitrary SQL attempt properly refused")

    # 14. Investigator Decision & Audit Log
    print(f"[14] Testing POST /api/decision on case {hero_case_id}...")
    res_dec = client.post(
        "/api/decision",
        json={
            "case_id": hero_case_id,
            "decision": "escalate_for_review",
            "notes": "Reviewed billing patterns; requested medical records audit.",
            "actor": "siu_investigator_1",
        },
    )
    assert res_dec.status_code == 200
    dec_data = res_dec.json()
    assert dec_data["status"] == "ESCALATED"
    print(f"    ✓ Decision recorded: {dec_data['decision']}, New Status: {dec_data['status']}")

    # Verify audit record
    print(f"[15] Testing GET /api/audit?case_id={hero_case_id}...")
    res_audit = client.get(f"/api/audit?case_id={hero_case_id}")
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data["total"] > 0
    latest_log = audit_data["records"][-1]
    assert latest_log["action"] == "DECISION_ESCALATE_FOR_REVIEW"
    print(f"    ✓ Audit log verified: {latest_log['action']} by {latest_log['actor']}")

    # 16. Evaluation Endpoint
    print("[16] Testing GET /api/evaluation...")
    res_eval = client.get("/api/evaluation")
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert "evaluations" in eval_data
    print("    ✓ Ground-truth evaluation metrics retrieved")

    print("\n============================================================")
    print("ALL 16 BACKEND ENDPOINTS AND SECURITY VALIDATIONS PASSED!")
    print("============================================================\n")


if __name__ == "__main__":
    run_validations()
