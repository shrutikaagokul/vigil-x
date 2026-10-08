"""Networks and fraud rings endpoints."""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from api.dependencies import get_db
from contracts.investigation import get_current_as_of
from db.queries import get_networks_list

router = APIRouter(prefix="/networks", tags=["Networks"])


@router.get("")
def list_networks(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve available network collusion rings and community summaries."""
    networks = get_networks_list(conn, limit=limit, offset=offset)
    return {
        "total": len(networks),
        "limit": limit,
        "offset": offset,
        "networks": networks,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }


@router.get("/{network_id}")
def get_network(network_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve details for a specific network cluster."""
    row = conn.execute("SELECT * FROM networks WHERE network_id = ?;", (network_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Network '{network_id}' not found.")
    data = dict(row)
    data["as_of"] = get_current_as_of()
    data["synthetic"] = True
    return data
