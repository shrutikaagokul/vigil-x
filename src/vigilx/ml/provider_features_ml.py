"""
Provider behavioral feature engineering for Vigil-X ML subsystem.

Builds a leakage-free, claim-derived provider-level feature table
for use by the Isolation Forest anomaly detector.

LEAKAGE RULES:
  - Ground truth labels are NEVER used as features.
  - All features are derived solely from observed claim behavior.
  - Future information (post-prediction-date) is excluded.

FEATURE GROUPS:
  Volume:      claim count, active days, members served
  Financial:   total/mean/median paid, billed ratio, log-spend
  Procedure:   CPT diversity, EM distribution, high-acuity share
  Utilization: visits-per-member, same-day rate, service-minutes
  Temporal:    burst ratio, weekend proportion
  Geographic:  member dispersion (std lat/lon)
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


PROVIDER_ANOMALY_FEATURE_VERSION = "1.0.0"


def build_provider_behavioral_features(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    snapshot_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute provider-level behavioral features from claim history.

    Parameters
    ----------
    claims : raw claims DataFrame (at minimum: provider_id, member_id,
             service_date, paid_amount, billed_amount, procedure_code,
             service_minutes, pos_code)
    providers : provider metadata (provider_id, specialty, latitude, longitude)
    snapshot_date : if given, only use claims with service_date <= snapshot_date.
                    Enforces temporal correctness for future-risk pipelines.

    Returns
    -------
    DataFrame indexed by provider_id with behavioral feature columns.
    All NaN values imputed with column medians.
    """
    claims = claims.copy()
    claims["service_date"] = pd.to_datetime(claims["service_date"], errors="coerce")

    if snapshot_date is not None:
        cutoff = pd.to_datetime(snapshot_date)
        claims = claims[claims["service_date"] <= cutoff]

    if claims.empty:
        return pd.DataFrame(columns=["provider_id"])

    # ------------------------------------------------------------------
    # E/M level extraction (re-use same logic as claim_features_ml)
    # ------------------------------------------------------------------
    def _em_level(code: str) -> int:
        if not isinstance(code, str):
            return 0
        code = code.upper().replace("CPT", "")
        em_map = {"99201": 1, "99202": 1, "99211": 1,
                  "99203": 2, "99212": 2,
                  "99204": 3, "99213": 3,
                  "99205": 4, "99214": 4,
                  "99215": 5}
        return em_map.get(code, 0)

    claims["_em_level"] = claims["procedure_code"].apply(_em_level)
    claims["_is_em"] = claims["_em_level"] > 0
    claims["_is_em45"] = claims["_em_level"] >= 4

    # ------------------------------------------------------------------
    # Per-claim aggregations grouped by provider
    # ------------------------------------------------------------------
    grp = claims.groupby("provider_id")

    # Volume
    vol = grp.agg(
        prov_claim_count=("claim_id", "count"),
        prov_unique_members=("member_id", "nunique"),
        prov_unique_cpts=("procedure_code", "nunique"),
        prov_active_days=("service_date", lambda x: (x.max() - x.min()).days + 1),
    ).reset_index()

    # Financial
    fin = grp.agg(
        prov_total_paid=("paid_amount", "sum"),
        prov_mean_paid=("paid_amount", "mean"),
        prov_median_paid=("paid_amount", "median"),
        prov_max_paid=("paid_amount", "max"),
        prov_std_paid=("paid_amount", "std"),
        prov_total_billed=("billed_amount", "sum"),
    ).reset_index()
    fin["prov_paid_to_billed_ratio"] = (
        fin["prov_total_paid"] / fin["prov_total_billed"].replace(0, np.nan)
    ).clip(0, 1)
    fin["prov_log_total_paid"] = np.log1p(fin["prov_total_paid"])

    # EM distribution
    em_grp = claims[claims["_is_em"]].groupby("provider_id")
    em_stats = em_grp.agg(
        prov_em_claim_count=("_em_level", "count"),
        prov_em45_count=("_is_em45", "sum"),
    ).reset_index()

    # Utilization / timing
    util = grp.agg(
        prov_mean_service_minutes=("service_minutes", "mean"),
        prov_median_service_minutes=("service_minutes", "median"),
    ).reset_index()
    util["prov_visits_per_member"] = (
        vol["prov_claim_count"].values / vol["prov_unique_members"].replace(0, np.nan).values
    )

    # Weekend/temporal
    claims["_dow"] = claims["service_date"].dt.dayofweek
    claims["_is_weekend"] = claims["_dow"] >= 5
    temp = grp.agg(
        prov_weekend_rate=("_is_weekend", "mean"),
        prov_claim_count_check=("claim_id", "count"),
    ).reset_index()

    # Burst: coefficient of variation in daily claim volume
    daily = claims.groupby(["provider_id", "service_date"])["claim_id"].count().reset_index()
    daily.columns = ["provider_id", "service_date", "daily_claims"]
    burst = daily.groupby("provider_id")["daily_claims"].agg(["mean", "std"]).reset_index()
    burst.columns = ["provider_id", "prov_daily_mean", "prov_daily_std"]
    burst["prov_burst_cv"] = (
        burst["prov_daily_std"] / burst["prov_daily_mean"].replace(0, np.nan)
    ).fillna(0)

    # Member geographic spread (proxy for unusual travel patterns)
    has_member_loc = (
        "member_id" in claims.columns and
        "latitude" in claims.columns and "longitude" in claims.columns
    )

    # Merge provider lat/lon onto claims for dispersion
    prov_loc = providers[["provider_id", "latitude", "longitude", "specialty"]].copy()
    claims_geo = claims.merge(prov_loc, on="provider_id", how="left")
    geo_disp = claims_geo.groupby("provider_id").agg(
        prov_lat=("latitude", "first"),
        prov_lon=("longitude", "first"),
    ).reset_index()

    # ------------------------------------------------------------------
    # Assemble all features
    # ------------------------------------------------------------------
    feat = (
        vol
        .merge(fin[["provider_id", "prov_total_paid", "prov_mean_paid", "prov_median_paid",
                     "prov_max_paid", "prov_std_paid", "prov_paid_to_billed_ratio",
                     "prov_log_total_paid"]], on="provider_id", how="left")
        .merge(em_stats, on="provider_id", how="left")
        .merge(util[["provider_id", "prov_mean_service_minutes", "prov_median_service_minutes",
                     "prov_visits_per_member"]], on="provider_id", how="left")
        .merge(temp[["provider_id", "prov_weekend_rate"]], on="provider_id", how="left")
        .merge(burst[["provider_id", "prov_daily_mean", "prov_daily_std", "prov_burst_cv"]],
               on="provider_id", how="left")
        .merge(geo_disp, on="provider_id", how="left")
        .merge(prov_loc[["provider_id", "specialty"]], on="provider_id", how="left")
    )

    feat["prov_em_claim_count"] = feat["prov_em_claim_count"].fillna(0)
    feat["prov_em45_count"] = feat["prov_em45_count"].fillna(0)
    feat["prov_em45_share"] = (
        feat["prov_em45_count"] / feat["prov_em_claim_count"].replace(0, np.nan)
    ).fillna(0)
    feat["prov_em_share"] = (
        feat["prov_em_claim_count"] / feat["prov_claim_count"].replace(0, np.nan)
    ).fillna(0)

    # Impute remaining NaNs with column medians
    numeric_cols = feat.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if feat[col].isna().any():
            feat[col] = feat[col].fillna(feat[col].median())

    return feat.reset_index(drop=True)


# Public list of feature columns used by the Isolation Forest model
PROVIDER_ANOMALY_FEATURES = [
    "prov_claim_count",
    "prov_unique_members",
    "prov_unique_cpts",
    "prov_active_days",
    "prov_total_paid",
    "prov_mean_paid",
    "prov_median_paid",
    "prov_max_paid",
    "prov_std_paid",
    "prov_paid_to_billed_ratio",
    "prov_log_total_paid",
    "prov_em_claim_count",
    "prov_em45_count",
    "prov_em45_share",
    "prov_em_share",
    "prov_mean_service_minutes",
    "prov_median_service_minutes",
    "prov_visits_per_member",
    "prov_weekend_rate",
    "prov_daily_mean",
    "prov_daily_std",
    "prov_burst_cv",
]
