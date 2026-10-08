"""Executive summary and funnel metrics endpoint."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends
from api.dependencies import get_db
from contracts.investigation import SummaryResponse
from db.queries import get_summary_metrics

router = APIRouter(tags=["Summary"])


@router.get("/summary", response_model=SummaryResponse)
def get_summary(conn: sqlite3.Connection = Depends(get_db)):
    """Return platform summary and investigation funnel statistics."""
    return get_summary_metrics(conn)
