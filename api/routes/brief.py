"""Investigation brief generation and retrieval endpoint."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from api.dependencies import get_db
from contracts.investigation import InvestigationBrief
from investigation.brief_generator import generate_investigation_brief
from investigation.evidence_packet import build_evidence_packet

router = APIRouter(prefix="/brief", tags=["Investigation Brief"])


@router.get("", response_model=InvestigationBrief)
def get_brief(
    case_id: str = Query(..., description="Target case ID"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Generate or retrieve a verified SIU investigation brief.
    Adheres strictly to the 6 mandatory investigative questions and deterministic verification.
    """
    try:
        packet = build_evidence_packet(conn, case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    brief = generate_investigation_brief(packet, use_llm_if_available=True)
    return brief
