"""Claims exploration endpoint for investigators."""
from __future__ import annotations

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_db
from contracts.investigation import get_current_as_of
from db.queries import get_claims_list

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.get("")
def list_claims(
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    member_id: Optional[str] = Query(None, description="Filter by member ID"),
    procedure_code: Optional[str] = Query(None, description="Filter by CPT/HCPCS code"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Filter and inspect claim records supporting an investigation."""
    claims = get_claims_list(
        conn,
        provider_id=provider_id,
        member_id=member_id,
        procedure_code=procedure_code,
        limit=limit,
        offset=offset,
    )
    return {
        "total": len(claims),
        "limit": limit,
        "offset": offset,
        "claims": claims,
        "as_of": get_current_as_of(),
        "synthetic": True,
    }
