"""
ML feature matrix assembly for Vigil-X Phase 1.

Assembles a clean, leakage-free claim-level feature matrix by
composing existing feature pipelines:
  - src/vigilx/features/claim_features.py
  - src/vigilx/features/provider_features.py
  - src/vigilx/features/member_features.py
  - temporal/features.py
  - geo/haversine.py

=============================================================
FEATURE INCLUSION / EXCLUSION DECISIONS
=============================================================

INCLUDED (leakage-safe, available at claim time):
  Claim-level raw:
    paid_amount, billed_amount, allowed_amount     — as-of values
    service_minutes                                — observed duration
    pos_code                                       — categorical
    claim_type                                     — categorical (professional/institutional)
    has_facility, has_referring_provider           — binary flags

  Engineered claim:
    paid_to_billed_ratio                           — charge capture ratio
    log_paid_amount                                — log-transform for skew
    service_day_of_week, is_weekend                — temporal pattern
    em_level                                       — CPT E/M severity 1-5 (0 if non-EM)

  Provider historical (from claims of this provider ≤ service_date):
    rolling_30d_claims, rolling_30d_dollars        — from temporal pipeline
    rolling_7d_claims                              — short-window burst signal
    rolling_90d_claims                             — long-window baseline
    provider_total_claims                          — volume
    provider_unique_members                        — reach
    provider_total_paid                            — financial footprint
    provider_visits_per_member                     — intensity
    provider_em_45_share                           — high-acuity coding share
    provider_specialty (categorical)               — specialty context

  Member historical:
    member_total_claims                            — utilization volume
    member_unique_providers                        — doctor-shopping proxy
    member_unique_cpts                             — complexity proxy
    member_days_since_last_claim                   — recency

  Geographic:
    dist_member_provider_miles                     — travel distance proxy

EXCLUDED:
  claim_id        — identifier; would cause pure memorization
  member_id       — high-cardinality identifier
  provider_id     — used as grouping key only; excluded as feature
  facility_id     — identifier
  referring_provider_id  — identifier
  service_date    — used for ordering/windowing only
  service_start_ts / service_end_ts  — post-booking timestamps (not pre-claim info)
  diagnosis_code  — high cardinality; deferred to Phase 2 with proper encoding
  procedure_code  — raw: deferred to Phase 2; em_level extracted instead
  status          — always "paid" in the dataset (constant → zero variance)
  is_suspicious   — ground truth TARGET, must never be a feature
  gt_claim_labels / gt_entity_labels / gt_scenarios — ground truth only
  Rule alert outputs (rule_id, severity, est_dollars from R01-R10) — rule leakage
  billed_amount alone — almost linear with paid_amount; ratio included instead
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

# Re-use existing pipelines — no reimplementation
from vigilx.features.claim_features import extract_em_level
from vigilx.features.provider_features import (
    compute_provider_em_distribution,
    compute_provider_utilization_stats,
)
from vigilx.features.member_features import compute_member_utilization

# Temporal pipeline lives at top-level module
try:
    from temporal.features import build_temporal_features
except ImportError:  # running from inside src/ during tests
    from importlib import import_module
    build_temporal_features = import_module("temporal.features").build_temporal_features

# Geographic pipeline
try:
    from geo.haversine import haversine_distance
except ImportError:
    from importlib import import_module
    haversine_distance = import_module("geo.haversine").haversine_distance


# ------------------------------------------------------------------
# Public constants
# ------------------------------------------------------------------

FEATURE_VERSION = "1.0.0"

#: Ordered list of numeric feature columns (for the LightGBM matrix).
NUMERIC_FEATURES: list[str] = [
    "paid_amount",
    "billed_amount",
    "allowed_amount",
    "paid_to_billed_ratio",
    "log_paid_amount",
    "service_minutes",
    "em_level",
    "has_facility",
    "has_referring_provider",
    "service_day_of_week",
    "is_weekend",
    # provider temporal (from temporal.features)
    "rolling_7d_claims",
    "rolling_30d_claims",
    "rolling_90d_claims",
    "rolling_30d_dollars",
    # provider utilization stats
    "provider_total_claims",
    "provider_unique_members",
    "provider_total_paid",
    "provider_visits_per_member",
    "provider_em_45_share",
    # member utilization
    "member_total_claims",
    "member_unique_providers",
    "member_unique_cpts",
    "member_days_since_last_claim",
    # geographic
    "dist_member_provider_miles",
]

#: Categorical feature columns for LightGBM native handling.
CATEGORICAL_FEATURES: list[str] = [
    "pos_code",
    "claim_type",
    "provider_specialty",
]

ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# ------------------------------------------------------------------
# Main assembly function
# ------------------------------------------------------------------


def build_claim_feature_matrix(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    members: pd.DataFrame,
    snapshot_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Assemble the leakage-free claim-level feature matrix.

    Parameters
    ----------
    claims : DataFrame
        Raw claims with columns as produced by the synthetic data generator.
    providers : DataFrame
        Provider table (latitude/longitude/specialty required for geo/peer).
    members : DataFrame
        Member table (latitude/longitude required for geo features).
    snapshot_date : str, optional
        ISO date string (YYYY-MM-DD). Temporal features are computed as-of
        this date. Defaults to the latest service_date in claims.

    Returns
    -------
    DataFrame with:
      - claim_id, provider_id  (keys, not model features)
      - ALL_FEATURES columns
      - All NaN filled with safe defaults (no NaN passed to LightGBM)
    """
    if claims.empty:
        return pd.DataFrame(columns=["claim_id", "provider_id"] + ALL_FEATURES)

    df = _prepare_base_columns(claims)
    df = _join_provider_static(df, providers)
    df = _join_member_static(df, members)
    df = _add_temporal_rolling(df, snapshot_date)
    df = _add_provider_utilization(df, claims)
    df = _add_member_utilization(df, claims, snapshot_date)
    df = _add_geographic_features(df, providers, members)
    df = _fill_missing(df)
    df = _enforce_types(df)

    key_cols = ["claim_id", "provider_id"]
    output_cols = key_cols + [c for c in ALL_FEATURES if c in df.columns]
    return df[output_cols].copy()


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _prepare_base_columns(claims: pd.DataFrame) -> pd.DataFrame:
    """Compute raw claim-level features from the claims table alone."""
    df = claims.copy()

    # --- Date handling ---
    df["service_date"] = pd.to_datetime(df["service_date"], errors="coerce")

    # --- Financial ratios ---
    paid = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0.0)
    billed = pd.to_numeric(df["billed_amount"], errors="coerce").fillna(0.0)
    allowed = pd.to_numeric(df["allowed_amount"], errors="coerce").fillna(0.0)

    df["paid_amount"] = paid
    df["billed_amount"] = billed
    df["allowed_amount"] = allowed

    # Avoid division by zero: if billed == 0, ratio = 1.0 (perfect payment)
    df["paid_to_billed_ratio"] = np.where(billed > 0, paid / billed, 1.0).clip(0.0, 2.0)
    df["log_paid_amount"] = np.log1p(paid)

    # --- Service duration ---
    df["service_minutes"] = pd.to_numeric(df.get("service_minutes", pd.Series()), errors="coerce").fillna(30.0)

    # --- Presence flags ---
    df["has_facility"] = df["facility_id"].notna().astype(int)
    df["has_referring_provider"] = df["referring_provider_id"].notna().astype(int)

    # --- Temporal pattern features ---
    df["service_day_of_week"] = df["service_date"].dt.dayofweek.fillna(0).astype(int)
    df["is_weekend"] = (df["service_day_of_week"] >= 5).astype(int)

    # --- E/M level (reuses existing feature pipeline) ---
    # extract_em_level expects 'cpt_code'; the synthetic data uses 'procedure_code'
    # We map procedure_code → cpt_code column temporarily.
    if "procedure_code" in df.columns and "cpt_code" not in df.columns:
        df = df.rename(columns={"procedure_code": "cpt_code"})

    df = extract_em_level(df)  # adds em_level; returns copy
    df["em_level"] = pd.to_numeric(df["em_level"], errors="coerce").fillna(0.0)

    # --- Categorical fields (keep as strings for LightGBM categorical handling) ---
    df["pos_code"] = df["pos_code"].astype(str).fillna("unknown")
    df["claim_type"] = df["claim_type"].astype(str).fillna("unknown")

    return df


def _join_provider_static(df: pd.DataFrame, providers: pd.DataFrame) -> pd.DataFrame:
    """Join provider specialty from the providers table."""
    if providers.empty or "provider_id" not in providers.columns:
        df["provider_specialty"] = "unknown"
        return df

    prov = providers[["provider_id", "specialty"]].copy()
    prov = prov.rename(columns={"specialty": "provider_specialty"})
    prov["provider_specialty"] = prov["provider_specialty"].astype(str).fillna("unknown")

    df = df.merge(prov, on="provider_id", how="left")
    df["provider_specialty"] = df["provider_specialty"].fillna("unknown")
    return df


def _join_member_static(df: pd.DataFrame, members: pd.DataFrame) -> pd.DataFrame:
    """Join member geo coords for distance computation later."""
    if members.empty or "member_id" not in members.columns:
        df["_member_lat"] = np.nan
        df["_member_lon"] = np.nan
        return df

    mem = members[["member_id", "latitude", "longitude"]].copy()
    mem = mem.rename(columns={"latitude": "_member_lat", "longitude": "_member_lon"})
    df = df.merge(mem, on="member_id", how="left")
    return df


def _add_temporal_rolling(df: pd.DataFrame, snapshot_date: Optional[str]) -> pd.DataFrame:
    """
    Add as-of safe rolling temporal features from temporal.features.

    build_temporal_features returns a daily panel. We merge the most
    recent panel row ≤ claim service_date for each (provider_id, service_date).
    """
    temporal_cols = [
        "rolling_7d_claims", "rolling_30d_claims",
        "rolling_90d_claims", "rolling_30d_dollars",
    ]

    # Need claim_id column for build_temporal_features
    work = df.copy()
    if "claim_id" not in work.columns and "cpt_code" in work.columns:
        # Already renamed; need a surrogate claim_id column for temporal
        pass

    # build_temporal_features expects 'service_date' and 'claim_id'
    try:
        panel = build_temporal_features(work, snapshot_date=snapshot_date)
    except Exception:
        for col in temporal_cols:
            df[col] = 0.0
        return df

    if panel.empty:
        for col in temporal_cols:
            df[col] = 0.0
        return df

    panel["service_date"] = pd.to_datetime(panel["service_date"])
    df["service_date"] = pd.to_datetime(df["service_date"])

    # Merge on exact (provider_id, service_date)
    panel_cols = ["provider_id", "service_date"] + [c for c in temporal_cols if c in panel.columns]
    panel_sub = panel[panel_cols].drop_duplicates(subset=["provider_id", "service_date"])

    df = df.merge(panel_sub, on=["provider_id", "service_date"], how="left")

    for col in temporal_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(0.0)

    return df


def _add_provider_utilization(df: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    """
    Join provider-level historical utilization stats.

    Uses compute_provider_utilization_stats and compute_provider_em_distribution
    from the existing provider_features pipeline. Both functions expect
    'billing_provider_id', so we alias if needed.
    """
    work = _alias_provider_col(claims)

    # compute_provider_em_distribution also needs 'em_level' and 'cpt_code'
    work_em = work.copy()
    if "procedure_code" in work_em.columns and "cpt_code" not in work_em.columns:
        work_em = work_em.rename(columns={"procedure_code": "cpt_code"})
    work_em = extract_em_level(work_em)

    util = compute_provider_utilization_stats(work)
    util = util.rename(columns={
        "billing_provider_id": "provider_id",
        "total_claims": "provider_total_claims",
        "unique_members": "provider_unique_members",
        "total_paid": "provider_total_paid",
        "visits_per_member": "provider_visits_per_member",
    })

    em_dist = compute_provider_em_distribution(work_em)
    em_dist = em_dist.rename(columns={"billing_provider_id": "provider_id"})

    # Join utilization stats
    df = df.merge(util[["provider_id", "provider_total_claims", "provider_unique_members",
                          "provider_total_paid", "provider_visits_per_member"]],
                  on="provider_id", how="left")

    # Join EM distribution (level_45_share)
    if not em_dist.empty and "level_45_share" in em_dist.columns:
        df = df.merge(em_dist[["provider_id", "level_45_share"]],
                      on="provider_id", how="left")
        df = df.rename(columns={"level_45_share": "provider_em_45_share"})
    else:
        df["provider_em_45_share"] = 0.0

    return df


def _add_member_utilization(
    df: pd.DataFrame,
    claims: pd.DataFrame,
    snapshot_date: Optional[str],
) -> pd.DataFrame:
    """
    Join member-level utilization stats (compute_member_utilization).

    compute_member_utilization expects 'service_from' column.
    The synthetic data uses 'service_date'. We alias it.
    """
    work = claims.copy()
    if "service_date" in work.columns and "service_from" not in work.columns:
        work = work.rename(columns={"service_date": "service_from"})
    # Also alias provider column
    if "provider_id" in work.columns and "billing_provider_id" not in work.columns:
        work["billing_provider_id"] = work["provider_id"]
    # Also alias cpt_code
    if "procedure_code" in work.columns and "cpt_code" not in work.columns:
        work = work.rename(columns={"procedure_code": "cpt_code"})

    ref_date = (
        pd.to_datetime(snapshot_date)
        if snapshot_date
        else pd.to_datetime(work["service_from"]).max()
    )

    mu = compute_member_utilization(work, reference_date=ref_date)
    mu = mu.rename(columns={
        "total_claims": "member_total_claims",
        "unique_providers": "member_unique_providers",
        "unique_cpts": "member_unique_cpts",
        "days_since_last_claim": "member_days_since_last_claim",
    })

    df = df.merge(mu[["member_id", "member_total_claims", "member_unique_providers",
                        "member_unique_cpts", "member_days_since_last_claim"]],
                  on="member_id", how="left")
    return df


def _add_geographic_features(
    df: pd.DataFrame,
    providers: pd.DataFrame,
    members: pd.DataFrame,
) -> pd.DataFrame:
    """Compute member-to-provider haversine distance per claim."""
    has_prov_geo = (
        not providers.empty
        and "latitude" in providers.columns
        and "longitude" in providers.columns
    )

    if not has_prov_geo or "_member_lat" not in df.columns:
        df["dist_member_provider_miles"] = 0.0
        # Clean up member lat/lon columns if they were added
        df.drop(columns=["_member_lat", "_member_lon"], inplace=True, errors="ignore")
        return df

    prov_geo = providers[["provider_id", "latitude", "longitude"]].copy()
    prov_geo = prov_geo.rename(columns={
        "latitude": "_prov_lat",
        "longitude": "_prov_lon",
    })

    df = df.merge(prov_geo, on="provider_id", how="left")

    df["dist_member_provider_miles"] = haversine_distance(
        df["_member_lat"].values,
        df["_member_lon"].values,
        df["_prov_lat"].values,
        df["_prov_lon"].values,
    )

    df.drop(columns=["_member_lat", "_member_lon", "_prov_lat", "_prov_lon"],
            inplace=True, errors="ignore")
    return df


def _fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NaN with safe sentinel values per feature type."""
    numeric_defaults: dict[str, float] = {
        "paid_amount": 0.0,
        "billed_amount": 0.0,
        "allowed_amount": 0.0,
        "paid_to_billed_ratio": 1.0,
        "log_paid_amount": 0.0,
        "service_minutes": 30.0,
        "em_level": 0.0,
        "has_facility": 0.0,
        "has_referring_provider": 0.0,
        "service_day_of_week": 0.0,
        "is_weekend": 0.0,
        "rolling_7d_claims": 0.0,
        "rolling_30d_claims": 0.0,
        "rolling_90d_claims": 0.0,
        "rolling_30d_dollars": 0.0,
        "provider_total_claims": 0.0,
        "provider_unique_members": 0.0,
        "provider_total_paid": 0.0,
        "provider_visits_per_member": 1.0,
        "provider_em_45_share": 0.0,
        "member_total_claims": 0.0,
        "member_unique_providers": 1.0,
        "member_unique_cpts": 0.0,
        "member_days_since_last_claim": 999.0,
        "dist_member_provider_miles": 0.0,
    }
    categorical_defaults: dict[str, str] = {
        "pos_code": "unknown",
        "claim_type": "unknown",
        "provider_specialty": "unknown",
    }

    for col, default in numeric_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)
        else:
            df[col] = default

    for col, default in categorical_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default).astype(str)
        else:
            df[col] = default

    return df


def _enforce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast numeric columns to float32; cast categoricals to pandas category dtype.

    LightGBM 4.x requires categorical columns to be pandas category dtype,
    not plain object/string. This enables LightGBM's native categorical splits.
    """
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = df[col].astype(np.float32)
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


def _alias_provider_col(claims: pd.DataFrame) -> pd.DataFrame:
    """Return a copy where provider_id is aliased to billing_provider_id."""
    work = claims.copy()
    if "provider_id" in work.columns and "billing_provider_id" not in work.columns:
        work["billing_provider_id"] = work["provider_id"]
    return work


# Backward compatibility alias
build_feature_matrix = build_claim_feature_matrix

