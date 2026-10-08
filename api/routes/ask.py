"""Restricted investigator Q&A endpoint."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_db
from contracts.investigation import QuestionRequest, QuestionResponse
from investigation.qa import answer_investigator_question

router = APIRouter(prefix="/ask", tags=["Investigator Q&A"])


@router.post("", response_model=QuestionResponse)
def ask_question(
    req: QuestionRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Answer an investigator question using ONLY whitelisted structured retrieval.
    Free-form SQL and ungrounded generation are prohibited.
    """
    if not req.case_id:
        raise HTTPException(status_code=400, detail="case_id is required.")
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty.")

    try:
        response = answer_investigator_question(conn, req.case_id, req.question)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
