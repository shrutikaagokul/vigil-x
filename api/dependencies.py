"""
FastAPI dependency injection for database connections.
"""
from __future__ import annotations

import sqlite3
from typing import Generator
from fastapi import Depends
from db.database import get_db_connection, DB_PATH


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Dependency that yields a managed SQLite database connection."""
    conn = get_db_connection(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
