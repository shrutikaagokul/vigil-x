"""
Peer-group feature engineering.

Robust peer-relative statistics (MAD z-scores, percentiles) used by R02, R03, R05.
Uses Median Absolute Deviation instead of mean/std for outlier robustness.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_mad_zscore(
    values: pd.Series,
    center: float | None = None,
) -> pd.Series:
    """
    Compute MAD-based z-score for a series of values.

    MAD z-score = (x - median) / (1.4826 * MAD)

    The constant 1.4826 makes MAD consistent with std for normal distributions.
    This is more robust to outliers than standard z-score.

    Parameters
    ----------
    values : pd.Series
        Numeric values to z-score.
    center : float, optional
        Override median. If None, computed from values.

    Returns
    -------
    pd.Series of z-scores. Returns 0 when MAD is 0 (all values identical).
    """
    if values.empty:
        return pd.Series(dtype=float)

    if center is None:
        center = values.median()

    mad = (values - center).abs().median()

    # Scale factor for consistency with normal distribution
    scaled_mad = 1.4826 * mad

    if scaled_mad == 0:
        # All values are identical (or nearly so) — no meaningful deviation
        return pd.Series(0.0, index=values.index)

    return (values - center) / scaled_mad


def compute_peer_stats(
    provider_metrics: pd.DataFrame,
    metric_col: str,
    peer_col: str = "peer_group",
) -> pd.DataFrame:
    """
    Compute peer-group statistics for a provider metric.

    Returns the original DataFrame with additional columns:
    - peer_median
    - peer_p95
    - peer_mad
    - peer_zscore (MAD-based)

    Parameters
    ----------
    provider_metrics : DataFrame
        Must contain ``metric_col`` and ``peer_col``.
    metric_col : str
        Name of the metric column to compare against peers.
    peer_col : str
        Column identifying peer group.
    """
    df = provider_metrics.copy()

    if df.empty or metric_col not in df.columns:
        for col in ["peer_median", "peer_p95", "peer_mad", "peer_zscore"]:
            df[col] = np.nan
        return df

    # If no peer_col, treat all providers as one group
    if peer_col not in df.columns:
        df[peer_col] = "all"

    peer_agg = df.groupby(peer_col)[metric_col].agg(
        peer_median="median",
        peer_p95=lambda x: x.quantile(0.95),
        peer_mad=lambda x: (x - x.median()).abs().median(),
    ).reset_index()

    df = df.merge(peer_agg, on=peer_col, how="left")

    # Compute MAD z-score within each peer group
    z_scores = []
    for _, group in df.groupby(peer_col):
        z = compute_mad_zscore(group[metric_col], center=group["peer_median"].iloc[0])
        z_scores.append(z)

    if z_scores:
        df["peer_zscore"] = pd.concat(z_scores).reindex(df.index)
    else:
        df["peer_zscore"] = 0.0

    return df


def compute_peer_duration_stats(
    claims: pd.DataFrame,
    peer_col: str = "peer_group",
) -> pd.DataFrame:
    """
    Compute peer-relative service duration statistics per CPT code.

    Returns DataFrame with: cpt_code, peer_group, duration_p25, duration_median.
    Used by R02 to identify suspiciously short service durations.
    """
    if claims.empty or "service_minutes" not in claims.columns:
        return pd.DataFrame(columns=["cpt_code", "duration_p25", "duration_median"])

    group_cols = ["cpt_code"]
    if peer_col in claims.columns:
        group_cols.append(peer_col)

    stats = claims.groupby(group_cols)["service_minutes"].agg(
        duration_p25=lambda x: x.quantile(0.25),
        duration_median="median",
    ).reset_index()

    return stats
