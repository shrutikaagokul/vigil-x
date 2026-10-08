"""SIU investigation queue endpoint."""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from api.dependencies import get_db
from contracts.investigation import QueueResponse, get_current_as_of
from db.queries import get_queue_items

router = APIRouter(tags=["Queue"])


@router.get("/queue", response_model=QueueResponse)
def get_queue(
    capacity_hours: Optional[float] = Query(None, description="Investigator capacity limit in hours", ge=0.0),
    horizon: Optional[int] = Query(30, description="Investigation time horizon in days", ge=1),
    sort: str = Query("priority", description="Sorting criteria: 'priority', 'ev_per_hour', or 'risk'"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Retrieve prioritized investigation queue items.
    Supports capacity-constrained allocation and EV-per-hour ranking.
    """
    valid_sorts = {"priority", "ev_per_hour", "risk"}
    if sort not in valid_sorts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort parameter '{sort}'. Allowed options: {sorted(list(valid_sorts))}",
        )

    items = get_queue_items(conn, capacity_hours=capacity_hours, horizon_days=horizon, sort_by=sort)

    # In REAL mode, missing analytical queue data is a dependency error
    from config.backend_config import is_real_mode
    if is_real_mode() and len(items) == 0:
        raise HTTPException(
            status_code=503,
            detail="Queue data unavailable in REAL mode: Upstream ML/Risk queue outputs have not been generated or loaded.",
        )

    return QueueResponse(
        total_cases=len(items),
        capacity_hours=capacity_hours or 0.0,
        horizon_days=horizon or 30,
        sort_applied=sort,
        items=items,
        as_of=get_current_as_of(),
        synthetic=True,
    )
