"""
Member-level feature engineering.

Shared functions for computing member-level features used by R01–R05.
"""

from __future__ import annotations

import pandas as pd


def compute_member_utilization(
    claims: pd.DataFrame,
    lookback_days: int = 365,
    reference_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Compute per-member utilization statistics.

    Returns a DataFrame indexed by member_id with:
    - total_claims: total claims in the evaluation window
    - unique_providers: distinct providers seen
    - unique_cpts: distinct CPT codes billed
    - chronic_count: from member table if available
    - days_since_last_claim: days between reference_date and most recent claim
    """
    if claims.empty or "member_id" not in claims.columns:
        return pd.DataFrame(columns=[
            "member_id", "total_claims", "unique_providers", "unique_cpts", "days_since_last_claim",
        ])

    df = claims.copy()
    if "service_from" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["service_from"]):
        df["service_from"] = pd.to_datetime(df["service_from"], errors="coerce")

    if reference_date is None:
        reference_date = df["service_from"].max() if "service_from" in df.columns else pd.Timestamp.now()

    if "service_from" in df.columns:
        window_start = reference_date - pd.Timedelta(days=lookback_days)
        # Temporal constraint: do not include future claims relative to reference_date
        df = df[(df["service_from"] >= window_start) & (df["service_from"] <= reference_date)]

    if df.empty:
        return pd.DataFrame(columns=[
            "member_id", "total_claims", "unique_providers", "unique_cpts", "days_since_last_claim",
        ])

    agg_kwargs: dict[str, tuple[str, str]] = {}
    if "claim_id" in df.columns:
        agg_kwargs["total_claims"] = ("claim_id", "nunique")
    elif "service_from" in df.columns:
        agg_kwargs["total_claims"] = ("service_from", "count")
    else:
        agg_kwargs["total_claims"] = ("member_id", "count")

    if "billing_provider_id" in df.columns:
        agg_kwargs["unique_providers"] = ("billing_provider_id", "nunique")
    if "cpt_code" in df.columns:
        agg_kwargs["unique_cpts"] = ("cpt_code", "nunique")
    if "service_from" in df.columns:
        agg_kwargs["last_claim_date"] = ("service_from", "max")

    stats = df.groupby("member_id").agg(**agg_kwargs).reset_index()

    if "unique_providers" not in stats.columns:
        stats["unique_providers"] = 0
    if "unique_cpts" not in stats.columns:
        stats["unique_cpts"] = 0

    if "last_claim_date" in stats.columns:
        stats["days_since_last_claim"] = (reference_date - stats["last_claim_date"]).dt.days
        stats.drop(columns=["last_claim_date"], inplace=True)
    else:
        stats["days_since_last_claim"] = 0

    return stats


def flag_ghost_members(
    claims: pd.DataFrame,
    lookback_months: int = 12,
    min_same_provider_claims: int = 5,
) -> pd.DataFrame:
    """
    Identify potential ghost members.

    A ghost member has:
    - No claims in the previous ``lookback_months``
    - 5+ claims with the same provider (in recent period)

    Returns DataFrame with columns: member_id, billing_provider_id, is_ghost.
    """
    if (
        claims.empty
        or "billing_provider_id" not in claims.columns
        or "member_id" not in claims.columns
        or "service_from" not in claims.columns
    ):
        return pd.DataFrame(columns=["member_id", "billing_provider_id", "is_ghost", "claim_count"])

    max_date = claims["service_from"].max()
    recent_start = max_date - pd.DateOffset(months=lookback_months)

    # Split into recent and historical
    recent = claims[claims["service_from"] > recent_start]
    historical = claims[claims["service_from"] <= recent_start]

    # Members with historical claims
    members_with_history = set(historical["member_id"].unique())

    # Recent member-provider pairs
    mp_counts = (
        recent.groupby(["member_id", "billing_provider_id"])
        .size()
        .reset_index(name="claim_count")
    )

    mp_counts["is_ghost"] = (
        (~mp_counts["member_id"].isin(members_with_history))
        & (mp_counts["claim_count"] >= min_same_provider_claims)
    )

    return mp_counts[["member_id", "billing_provider_id", "is_ghost", "claim_count"]]
