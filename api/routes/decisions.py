"""Investigator case decision endpoint."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_db
from contracts.investigation import (
    CaseStatus,
    DecisionRequest,
    DecisionResponse,
    DecisionType,
)
from db.queries import get_case_by_id, record_case_decision

router = APIRouter(prefix="/decision", tags=["Decisions"])


@router.post("", response_model=DecisionResponse)
def make_decision(
    req: DecisionRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Record an investigator disposition (accept, reject, escalate_for_review).
    Appends an immutable entry to the audit log.
    """
    case = get_case_by_id(conn, req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{req.case_id}' not found.")

    res = record_case_decision(
        conn,
        case_id=req.case_id,
        decision=req.decision.value,
        notes=req.notes or "",
        actor=req.actor,
    )

    return DecisionResponse(
        case_id=res["case_id"],
        status=CaseStatus(res["status"]),
        decision=res["decision"],
        recorded_at=res["recorded_at"],
        audit_id=res["audit_id"],
        message=res["message"],
        as_of=res["recorded_at"],
        synthetic=True,
    )
