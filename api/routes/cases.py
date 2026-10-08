"""Investigation cases and evidence endpoints."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_db
from contracts.investigation import (
    BaseApiResponse,
    CaseDetail,
    CaseEvidenceItem,
    get_current_as_of,
)
from db.queries import (
    get_case_by_id,
    get_case_evidence_ledger,
    get_case_network,
    get_case_timeline,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.get("/{case_id}")
def get_case(case_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve complete investigation case details."""
    case = get_case_by_id(conn, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    data = case.model_dump()
    data["as_of"] = get_current_as_of()
    data["synthetic"] = True
    return data


@router.get("/{case_id}/evidence")
def get_case_evidence(case_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve full evidence ledger for a case with item-level provenance."""
    case = get_case_by_id(conn, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    ledger = get_case_evidence_ledger(conn, case_id)
    return {
        "case_id": case_id,
        "total_evidence_items": len(ledger),
        "evidence": [item.model_dump() for item in ledger],
        "as_of": get_current_as_of(),
        "synthetic": True,
    }


@router.get("/{case_id}/timeline")
def get_timeline(case_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve chronological investigation events and relevant claim activity."""
    case = get_case_by_id(conn, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    timeline = get_case_timeline(conn, case_id)
    return {
        "case_id": case_id,
        "events_count": len(timeline),
        "timeline": timeline,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }


@router.get("/{case_id}/network")
def get_network(case_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve case-centered subgraph for frontend visualization."""
    case = get_case_by_id(conn, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    subgraph = get_case_network(conn, case_id)
    return {
        "case_id": case_id,
        "subgraph": subgraph,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }
