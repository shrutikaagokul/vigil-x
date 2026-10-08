"""
Provider-level feature engineering.

Shared functions for computing provider-level features used by R01–R05.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_provider_em_distribution(claims: pd.DataFrame) -> pd.DataFrame:
    """
    Compute E/M level distribution per provider.

    Returns a DataFrame with:
    - billing_provider_id
    - total_em_claims
    - level_{1..5}_count
    - level_{1..5}_share
    - level_45_share  (combined Level 4 + Level 5 share)
    """
    em_claims = claims[claims["em_level"].notna()].copy()

    if em_claims.empty:
        return pd.DataFrame(columns=[
            "billing_provider_id", "total_em_claims",
            "level_45_share",
        ])

    em_claims["em_level"] = em_claims["em_level"].astype(int)

    # Pivot: count per provider per level
    pivot = (
        em_claims.groupby(["billing_provider_id", "em_level"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Rename columns
    for lvl in range(1, 6):
        if lvl not in pivot.columns:
            pivot[lvl] = 0

    # Compute totals and shares
    level_cols = [c for c in pivot.columns if isinstance(c, (int, np.integer))]
    pivot["total_em_claims"] = pivot[level_cols].sum(axis=1)

    for lvl in range(1, 6):
        pivot[f"level_{lvl}_count"] = pivot.get(lvl, 0)
        pivot[f"level_{lvl}_share"] = pivot[f"level_{lvl}_count"] / pivot["total_em_claims"]

    pivot["level_45_share"] = pivot["level_4_share"] + pivot["level_5_share"]

    # Clean up
    result_cols = (
        ["billing_provider_id", "total_em_claims"]
        + [f"level_{i}_count" for i in range(1, 6)]
        + [f"level_{i}_share" for i in range(1, 6)]
        + ["level_45_share"]
    )
    return pivot[[c for c in result_cols if c in pivot.columns]].copy()


def compute_provider_utilization_stats(claims: pd.DataFrame) -> pd.DataFrame:
    """
    Compute provider-level utilization statistics.

    Returns DataFrame with:
    - billing_provider_id
    - total_claims, unique_members, total_paid
    - visits_per_member
    """
    if claims.empty:
        return pd.DataFrame(columns=[
            "billing_provider_id", "total_claims", "unique_members",
            "total_paid", "visits_per_member",
        ])

    paid_col = "paid_amount" if "paid_amount" in claims.columns else "allowed_amount"
    if paid_col not in claims.columns:
        paid_col = "billed_amount"

    count_col = "claim_id" if "claim_id" in claims.columns else "member_id"

    stats = claims.groupby("billing_provider_id").agg(
        total_claims=(count_col, "count"),
        unique_members=("member_id", "nunique"),
    ).reset_index()

    if paid_col in claims.columns:
        paid = claims.groupby("billing_provider_id")[paid_col].sum().reset_index()
        paid.columns = ["billing_provider_id", "total_paid"]
        stats = stats.merge(paid, on="billing_provider_id", how="left")
    else:
        stats["total_paid"] = 0.0

    stats["visits_per_member"] = stats["total_claims"] / stats["unique_members"].clip(lower=1)
    return stats


def compute_provider_unbundling_rate(
    claims: pd.DataFrame,
    bundling_pairs: pd.DataFrame,
    override_modifiers: list[str],
) -> pd.DataFrame:
    """
    Compute per-provider unbundling rate.

    Rate = (unbundled claim-days) / (total claim-days with bundleable codes)

    Parameters
    ----------
    claims : DataFrame
        Must have: member_id, billing_provider_id, cpt_code, service_from, modifier
    bundling_pairs : DataFrame
        Must have: comprehensive_cpt, component_cpt
    override_modifiers : list[str]
        Modifiers that legitimately override bundling (e.g., "59", "25", "XE")

    Returns
    -------
    DataFrame with: billing_provider_id, unbundling_rate, total_bundleable_days, unbundled_days
    """
    if claims.empty or bundling_pairs.empty:
        return pd.DataFrame(columns=[
            "billing_provider_id", "unbundling_rate",
            "total_bundleable_days", "unbundled_days",
        ])

    # Get all codes involved in bundling pairs
    comp_codes = set(bundling_pairs["comprehensive_cpt"].unique())
    component_codes = set(bundling_pairs["component_cpt"].unique())
    all_bundle_codes = comp_codes | component_codes

    # Filter to claims with bundleable codes
    bundle_claims = claims[claims["cpt_code"].isin(all_bundle_codes)].copy()
    if bundle_claims.empty:
        return pd.DataFrame(columns=[
            "billing_provider_id", "unbundling_rate",
            "total_bundleable_days", "unbundled_days",
        ])

    # Group by provider-member-date
    grouped = bundle_claims.groupby(
        ["billing_provider_id", "member_id", "service_from"]
    ).agg(
        cpts=("cpt_code", set),
        modifiers=("modifier", lambda x: set(str(m) for m in x if pd.notna(m))),
    ).reset_index()

    def _has_unbundled(row):
        cpts = row["cpts"]
        mods = row["modifiers"]
        # Check if any override modifier is present
        if mods & set(override_modifiers):
            return False
        # Check if both comprehensive and component present
        for _, pair in bundling_pairs.iterrows():
            if pair["comprehensive_cpt"] in cpts and pair["component_cpt"] in cpts:
                return True
        return False

    grouped["is_unbundled"] = grouped.apply(_has_unbundled, axis=1)

    # Compute rate per provider
    provider_stats = grouped.groupby("billing_provider_id").agg(
        total_bundleable_days=("is_unbundled", "count"),
        unbundled_days=("is_unbundled", "sum"),
    ).reset_index()

    provider_stats["unbundling_rate"] = (
        provider_stats["unbundled_days"] / provider_stats["total_bundleable_days"].clip(lower=1)
    )
    return provider_stats
