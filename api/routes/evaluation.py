"""Evaluation and benchmark metrics endpoint."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends
from api.dependencies import get_db
from contracts.investigation import get_current_as_of
from db.queries import get_evaluation_metrics_data

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.get("")
def get_evaluation(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve ground-truth evaluation, ring recovery rates, and baseline metrics."""
    data = get_evaluation_metrics_data(conn)
    data["as_of"] = get_current_as_of()
    data["synthetic"] = True
    return data
