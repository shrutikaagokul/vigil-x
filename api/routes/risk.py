"""Risk signals and scores endpoint."""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_db
from contracts.investigation import get_current_as_of
from db.queries import get_risk_info

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("")
def list_risk_scores(
    entity_id: Optional[str] = Query(None, description="Optional focal entity ID"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Expose upstream risk scores and risk component signals.
    Does not recalculate formulas; surfaces stored analytical pipeline outputs.
    """
    results = get_risk_info(conn, entity_id=entity_id)
    return {
        "total": len(results),
        "scores": results,
        "risk_scores": results,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }
