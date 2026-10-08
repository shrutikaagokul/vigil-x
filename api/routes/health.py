"""
Health check and readiness endpoint for Vigil-X.

Distinguishes:
- API alive
- DB reachable
- DB schema valid
- required data available
- data mode ('fixture' vs 'real')
- optional ML outputs available
- optional LLM available
"""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends, Response, status
from api.dependencies import get_db
from config.backend_config import check_llm_available, get_data_mode
from contracts.investigation import get_current_as_of

router = APIRouter(tags=["Health"])

REQUIRED_TABLES = [
    "providers",
    "members",
    "facilities",
    "claims",
    "claim_lines",
    "referrals",
    "alerts",
    "cases",
    "case_evidence",
    "queue_items",
    "networks",
    "risk_scores",
    "audit_log",
]


@router.get("/health")
def get_health(response: Response, conn: sqlite3.Connection = Depends(get_db)):
    """
    Readiness and health check verifying SQLite schema, domain data, and ML pipeline readiness.
    """
    db_reachable = False
    schema_valid = False
    required_data_available = False
    ml_outputs_available = False
    table_count = 0
    data_mode = get_data_mode().value

    try:
        # 1. DB Reachable
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r["name"] for r in cursor.fetchall()]
        table_count = len(tables)
        db_reachable = True

        # 2. Schema valid
        missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
        schema_valid = (len(missing_tables) == 0)

        # 3. Required data available
        if schema_valid:
            p_cnt = conn.execute("SELECT COUNT(*) AS c FROM providers;").fetchone()["c"]
            c_cnt = conn.execute("SELECT COUNT(*) AS c FROM claims;").fetchone()["c"]
            required_data_available = (p_cnt > 0 and c_cnt > 0)

            # 4. Optional ML / Queue outputs available
            q_cnt = conn.execute("SELECT COUNT(*) AS c FROM queue_items;").fetchone()["c"]
            cases_cnt = conn.execute("SELECT COUNT(*) AS c FROM cases;").fetchone()["c"]
            ml_outputs_available = (q_cnt > 0 and cases_cnt > 0)

    except Exception:
        db_reachable = False

    llm_available = check_llm_available()

    # Determine overall readiness status
    if db_reachable and schema_valid and required_data_available:
        readiness_status = "healthy"
    elif db_reachable and schema_valid:
        readiness_status = "degraded"  # Schema present but data not loaded yet
    else:
        readiness_status = "uninitialized"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": readiness_status,
        "database": "ready" if db_reachable and schema_valid else "missing_tables",
        "api_alive": True,
        "database_reachable": db_reachable,
        "schema_valid": schema_valid,
        "data_mode": data_mode,
        "required_data_available": required_data_available,
        "ml_outputs_available": ml_outputs_available,
        "llm_available": llm_available,
        "table_count": table_count,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }
