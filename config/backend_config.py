"""
Backend and Data Mode Configuration for Vigil-X.

Explicitly manages:
- DATA_MODE ('fixture' vs 'real')
- Database path
- Analytical artifact source paths
- LLM credential availability
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional


class DataMode(str, Enum):
    FIXTURE = "fixture"
    REAL = "real"


def get_data_mode() -> DataMode:
    """
    Get current configured data mode.
    Reads VIGILX_DATA_MODE or DATA_MODE environment variable.
    Defaults to DataMode.FIXTURE to unblock UI and API testing.
    """
    val = os.environ.get("VIGILX_DATA_MODE") or os.environ.get("DATA_MODE", "fixture")
    val_clean = val.strip().lower()
    if val_clean == "real":
        return DataMode.REAL
    return DataMode.FIXTURE


def is_real_mode() -> bool:
    """Return True if running in real analytical output mode."""
    return get_data_mode() == DataMode.REAL


def is_fixture_mode() -> bool:
    """Return True if running in deterministic fixture mode."""
    return get_data_mode() == DataMode.FIXTURE


def get_db_path() -> Path:
    """Return target SQLite database path."""
    return Path(os.environ.get("VIGILX_DB_PATH", "app.db"))


def check_llm_available() -> bool:
    """Check if any supported LLM API key is present in environment."""
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )


def get_default_currency() -> str:
    """
    Return default currency designation for monetary values (USD).
    Configurable via VIGILX_CURRENCY env var if needed.
    """
    return os.environ.get("VIGILX_CURRENCY", "USD").upper().strip()

