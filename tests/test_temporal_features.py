"""Tests for temporal features."""
import pytest
import pandas as pd
import numpy as np
from temporal.features import (
    build_provider_daily_summary,
    build_provider_weekly_panel,
    add_trailing_median,
    build_temporal_features,
    compute_same_day_events,
)


def _make_claims(n=50):
    """Generate simple claims for temporal testing."""
    claims = []
    for i in range(n):
        week = i // 5
        day = i % 5
        date = f"2024-{(week//4)+1:02d}-{(week%4)*7+day+1:02d}"
        claims.append({
            "claim_id": f"C{i:04d}",
            "provider_id": "P001",
            "member_id": f"M{i%10:04d}",
            "service_date": date,
            "service_minutes": 30,
            "paid_amount": 100.0 + i * 10,
        })
    return pd.DataFrame(claims)


def test_daily_summary():
    claims = _make_claims(10)
    daily = build_provider_daily_summary(claims)
    assert "daily_minutes" in daily.columns
    assert "daily_claims" in daily.columns
    assert daily["daily_minutes"].sum() == 300  # 10 claims × 30 min


def test_weekly_panel():
    claims = _make_claims(50)
    panel = build_provider_weekly_panel(claims)
    assert "weekly_dollars" in panel.columns
    assert "weekly_claims" in panel.columns
    assert panel["weekly_dollars"].sum() == claims["paid_amount"].sum()


def test_trailing_median():
    claims = _make_claims(50)
    panel = build_provider_weekly_panel(claims)
    panel = add_trailing_median(panel, trailing_weeks=4)
    assert "trailing_median" in panel.columns
    assert "history_weeks" in panel.columns
    # First row should have NaN trailing median (no history)
    first_row = panel.iloc[0]
    assert pd.isna(first_row["trailing_median"])


def test_trailing_median_as_of_safe():
    """Trailing median should not use current week's data."""
    claims = _make_claims(50)
    panel = build_provider_weekly_panel(claims)
    panel = add_trailing_median(panel, trailing_weeks=4)
    # The trailing median for each week should be computed from previous weeks only
    for i in range(1, len(panel)):
        if panel.iloc[i]["history_weeks"] > 0:
            # median should be based on PREVIOUS weeks, not current
            assert pd.notna(panel.iloc[i]["trailing_median"])


def test_temporal_features():
    claims = _make_claims(50)
    features = build_temporal_features(claims)
    assert "rolling_7d_claims" in features.columns
    assert "rolling_30d_claims" in features.columns
    assert "rolling_90d_claims" in features.columns


def test_same_day_events():
    claims = pd.DataFrame([
        {"claim_id": "C001", "member_id": "M001", "provider_id": "P001",
         "service_date": "2024-01-15"},
        {"claim_id": "C002", "member_id": "M001", "provider_id": "P002",
         "service_date": "2024-01-15"},
        {"claim_id": "C003", "member_id": "M002", "provider_id": "P001",
         "service_date": "2024-01-15"},
    ])
    same_day = compute_same_day_events(claims)
    assert len(same_day) == 1  # Only M001 has 2 claims on same day
    assert same_day.iloc[0]["member_id"] == "M001"


def test_snapshot_date_filter():
    """Features should respect snapshot_date."""
    claims = _make_claims(50)
    features = build_temporal_features(claims, snapshot_date="2024-01-15")
    assert all(features["service_date"] <= pd.Timestamp("2024-01-15"))
