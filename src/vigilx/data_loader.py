"""
Data loader for Vigil-X synthetic healthcare data.

Loads CSV files from the data directory into a dict of DataFrames.
Handles date parsing and basic type coercion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


# Expected CSV table names and their date columns
_DATE_COLUMNS: dict[str, list[str]] = {
    "claims": ["service_from", "service_to", "submission_date", "paid_date"],
    "claim_lines": ["service_from", "service_to"],
    "members": ["dob", "death_date", "enrollment_start", "enrollment_end"],
    "providers": ["open_date", "close_date"],
    "facilities": ["open_date", "close_date"],
    "inpatient_stays": ["admission_date", "discharge_date"],
}


def load_data(data_dir: str | Path) -> dict[str, Any]:
    """
    Load all CSV files from a data directory.

    Parameters
    ----------
    data_dir : str or Path
        Path to directory containing CSV files.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary keyed by table name (filename without extension).
    """
    data_dir = Path(data_dir)
    data: dict[str, pd.DataFrame] = {}

    for csv_path in sorted(data_dir.glob("*.csv")):
        table_name = csv_path.stem
        df = pd.read_csv(csv_path, low_memory=False)

        # Parse date columns if known
        date_cols = _DATE_COLUMNS.get(table_name, [])
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        data[table_name] = df

    return data
