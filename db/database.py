"""
Database connection management for Vigil-X SQLite application database.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

DEFAULT_DB_PATH = Path(os.environ.get("VIGILX_DB_PATH", "app.db"))
DB_PATH = DEFAULT_DB_PATH


def get_db_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """
    Open and configure a SQLite database connection.

    Enables WAL mode and Row factory for dictionary-like column access.
    """
    target_path = str(db_path or DB_PATH)
    conn = sqlite3.connect(target_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Performance and integrity pragmas
    if target_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


@contextmanager
def get_db_context(db_path: Optional[str | Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections that commits and closes safely."""
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[str | Path] = None) -> None:
    """Initialize database tables and indexes."""
    from db.schema import init_schema
    with get_db_context(db_path) as conn:
        init_schema(conn)
