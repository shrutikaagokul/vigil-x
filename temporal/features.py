"""
Temporal feature engineering for Vigil-X.

All features are as-of safe: they only use data available
before the snapshot date. No future data leakage.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def build_provider_daily_summary(claims: pd.DataFrame) -> pd.DataFrame:
    """
    Build provider daily summary: total service minutes and claim count per day.

    Args:
        claims: DataFrame with columns [provider_id, service_date, service_minutes]

    Returns:
        DataFrame with columns [provider_id, service_date, daily_minutes, daily_claims]
    """
    df = claims.copy()
    df["service_date"] = pd.to_datetime(df["service_date"])
    df["service_minutes"] = pd.to_numeric(df["service_minutes"], errors="coerce").fillna(0)

    daily = (
        df.groupby(["provider_id", "service_date"])
        .agg(
            daily_minutes=("service_minutes", "sum"),
            daily_claims=("claim_id", "count"),
        )
        .reset_index()
    )
    return daily


def build_provider_weekly_panel(
    claims: pd.DataFrame,
    date_col: str = "service_date",
    amount_col: str = "paid_amount",
) -> pd.DataFrame:
    """
    Build provider weekly paid-dollar panel.

    Groups by provider and ISO week. As-of safe: each row only reflects
    that week's actual activity.

    Returns:
        DataFrame with columns [provider_id, week_start, weekly_dollars, weekly_claims]
    """
    df = claims.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    # Use Monday-based week start
    df["week_start"] = df[date_col] - pd.to_timedelta(df[date_col].dt.dayofweek, unit="D")
    df["week_start"] = df["week_start"].dt.normalize()

    panel = (
        df.groupby(["provider_id", "week_start"])
        .agg(
            weekly_dollars=(amount_col, "sum"),
            weekly_claims=("claim_id", "count"),
        )
        .reset_index()
        .sort_values(["provider_id", "week_start"])
    )
    return panel


def add_trailing_median(
    panel: pd.DataFrame,
    trailing_weeks: int = 12,
    value_col: str = "weekly_dollars",
) -> pd.DataFrame:
    """
    Add trailing N-week median to a weekly panel. As-of safe.

    The trailing median for week W uses weeks [W-trailing_weeks, W-1].
    Week W itself is NOT included.
    """
    panel = panel.sort_values(["provider_id", "week_start"]).copy()

    def _trailing_median(group):
        vals = group[value_col].values
        medians = []
        for i in range(len(vals)):
            start = max(0, i - trailing_weeks)
            window = vals[start:i]  # excludes current week
            if len(window) > 0:
                medians.append(np.median(window))
            else:
                medians.append(np.nan)
        group["trailing_median"] = medians
        group["history_weeks"] = [min(i, trailing_weeks) for i in range(len(vals))]
        return group

    panel = panel.groupby("provider_id", group_keys=False).apply(_trailing_median)
    return panel


def build_temporal_features(
    claims: pd.DataFrame,
    snapshot_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build rolling temporal features per provider.

    Features:
    - rolling 7-day claim count and dollars
    - rolling 30-day claim count and dollars
    - rolling 90-day claim count and dollars

    All features are as-of safe (only use data <= snapshot_date).
    """
    df = claims.copy()
    df["service_date"] = pd.to_datetime(df["service_date"])
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)

    if snapshot_date:
        df = df[df["service_date"] <= pd.to_datetime(snapshot_date)]

    # Daily aggregation first
    daily = (
        df.groupby(["provider_id", "service_date"])
        .agg(
            day_claims=("claim_id", "count"),
            day_dollars=("paid_amount", "sum"),
        )
        .reset_index()
        .sort_values(["provider_id", "service_date"])
    )

    # Build rolling features per provider
    daily = daily.set_index("service_date")
    features_list = []

    for pid, group in daily.groupby("provider_id"):
        # Ensure continuous date range for rolling
        if len(group) == 0:
            continue
        date_range = pd.date_range(group.index.min(), group.index.max(), freq="D")
        expanded = group.reindex(date_range).fillna(0)
        expanded["provider_id"] = pid

        for window, label in [(7, "7d"), (30, "30d"), (90, "90d")]:
            expanded[f"rolling_{label}_claims"] = (
                expanded["day_claims"].rolling(window, min_periods=1).sum()
            )
            expanded[f"rolling_{label}_dollars"] = (
                expanded["day_dollars"].rolling(window, min_periods=1).sum()
            )

        expanded.index.name = "service_date"
        features_list.append(expanded.reset_index())

    if not features_list:
        return pd.DataFrame()

    result = pd.concat(features_list, ignore_index=True)
    return result


def compute_referral_history(
    referrals: pd.DataFrame,
    trailing_days: int = 90,
) -> pd.DataFrame:
    """
    Compute referral counts per provider over trailing window.

    Returns per-provider per-period referral statistics.
    """
    df = referrals.copy()
    df["referral_date"] = pd.to_datetime(df["referral_date"])

    # Total referrals sent per provider
    sent = (
        df.groupby("referring_provider_id")
        .agg(
            total_referrals_sent=("referral_id", "count"),
            referral_start=("referral_date", "min"),
            referral_end=("referral_date", "max"),
        )
        .reset_index()
        .rename(columns={"referring_provider_id": "provider_id"})
    )

    # Per-target referral concentration
    by_target = (
        df.groupby(["referring_provider_id", "target_provider_id"])
        .agg(referrals_to_target=("referral_id", "count"))
        .reset_index()
    )

    return sent, by_target


def compute_same_day_events(claims: pd.DataFrame) -> pd.DataFrame:
    """
    Identify same-day events: claims by the same member on the same service date.

    Returns a DataFrame of (member_id, service_date, claim_ids, provider_ids).
    """
    df = claims.copy()
    df["service_date"] = pd.to_datetime(df["service_date"])

    same_day = (
        df.groupby(["member_id", "service_date"])
        .agg(
            claim_ids=("claim_id", list),
            provider_ids=("provider_id", list),
            claim_count=("claim_id", "count"),
        )
        .reset_index()
    )
    # Only keep days with multiple claims
    same_day = same_day[same_day["claim_count"] > 1].copy()
    return same_day
