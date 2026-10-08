"""
Tests for data loader module.

Covers:
  1. Loading CSVs into dictionary of DataFrames
  2. Automatic datetime parsing for recognized date columns
  3. Empty directory handling
"""

from pathlib import Path
import pandas as pd
import pytest

from vigilx.data_loader import load_data


class TestDataLoader:

    def test_load_data(self, tmp_path: Path):
        # Create test CSV files
        claims_csv = tmp_path / "claims.csv"
        claims_df = pd.DataFrame([
            {
                "claim_id": "C1",
                "service_from": "2024-01-15",
                "service_to": "2024-01-15",
                "allowed_amount": 100.0,
            }
        ])
        claims_df.to_csv(claims_csv, index=False)

        members_csv = tmp_path / "members.csv"
        members_df = pd.DataFrame([
            {
                "member_id": "M1",
                "dob": "1980-05-12",
                "enrollment_end": "2024-12-31",
            }
        ])
        members_df.to_csv(members_csv, index=False)

        data = load_data(tmp_path)

        assert "claims" in data
        assert "members" in data
        assert len(data["claims"]) == 1
        assert pd.api.types.is_datetime64_any_dtype(data["claims"]["service_from"])
        assert pd.api.types.is_datetime64_any_dtype(data["members"]["dob"])

    def test_empty_directory(self, tmp_path: Path):
        data = load_data(tmp_path)
        assert data == {}
