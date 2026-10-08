"""Providers directory and lookup endpoints."""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from api.dependencies import get_db
from contracts.investigation import get_current_as_of
from db.queries import get_providers_list

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.get("")
def list_providers(
    provider_id: Optional[str] = Query(None, description="Exact provider ID filter"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    county: Optional[str] = Query(None, description="Filter by county"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Search and filter provider records."""
    providers = get_providers_list(
        conn,
        provider_id=provider_id,
        specialty=specialty,
        county=county,
        limit=limit,
        offset=offset,
    )
    return {
        "total": len(providers),
        "limit": limit,
        "offset": offset,
        "providers": providers,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }


@router.get("/{provider_id}")
def get_provider(provider_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve detailed provider enrollment and profile information."""
    row = conn.execute("SELECT * FROM providers WHERE provider_id = ?;", (provider_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    data = dict(row)
    data["as_of"] = get_current_as_of()
    data["synthetic"] = True
    return data
