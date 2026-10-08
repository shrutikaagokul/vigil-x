"""Audit log exploration endpoint."""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_db
from contracts.investigation import get_current_as_of
from db.queries import get_audit_records

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
def list_audit_log(
    case_id: Optional[str] = Query(None, description="Filter audit events by case ID"),
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve immutable audit history of automated actions and investigator decisions."""
    records = get_audit_records(conn, case_id=case_id, limit=limit)
    return {
        "total": len(records),
        "limit": limit,
        "records": [r.model_dump() for r in records],
        "as_of": get_current_as_of(),
        "synthetic": True,
    }
