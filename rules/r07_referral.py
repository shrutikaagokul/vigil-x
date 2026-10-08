"""
R07 — Referral Anomaly

Detects four referral patterns:
A. Referral concentration (>70% to one target, min 20 referrals)
B. Reciprocal referral loops (A→B and B→A, each >=15 referrals)
C. Same-day referral to high-cost laboratory
D. Referral spike (z-score >3 vs trailing 90-day history)

False-positive considerations: rural areas, single-specialist regions,
employed medical groups, documented ownership relationships.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from contracts.alert import Alert, Evidence, Severity
from config.loader import get_rule_config

RULE_ID = "R07"


def detect_referral_anomaly(
    claims: pd.DataFrame,
    referrals: pd.DataFrame,
    providers: Optional[pd.DataFrame] = None,
    config: Optional[Dict] = None,
) -> List[Alert]:
    """
    Run all R07 sub-rules and return alerts.
    """
    if config is None:
        config = get_rule_config("R07")

    if not config.get("enabled", True):
        return []

    version = config.get("version", "1.0.0")
    alerts: List[Alert] = []

    if referrals.empty:
        return alerts

    alerts.extend(_detect_concentration(referrals, providers, config, version))
    alerts.extend(_detect_reciprocal_loop(referrals, config, version))
    alerts.extend(_detect_same_day_lab(claims, referrals, providers, config, version))
    alerts.extend(_detect_referral_spike(referrals, config, version))

    return alerts


# ---------- A: Referral concentration ----------

def _detect_concentration(
    referrals: pd.DataFrame,
    providers: Optional[pd.DataFrame],
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag providers sending >70% of referrals to one target."""
    threshold = config.get("concentration_threshold", 0.70)
    min_count = config.get("min_referral_count", 20)
    severity = config.get("severity", Severity.MEDIUM.value)

    df = referrals.copy()

    # Total referrals per referring provider
    totals = df.groupby("referring_provider_id").agg(
        total=("referral_id", "count")
    ).reset_index()
    totals = totals[totals["total"] >= min_count]

    if totals.empty:
        return []

    # Per-target counts
    by_target = df.groupby(["referring_provider_id", "target_provider_id"]).agg(
        count=("referral_id", "count"),
        claim_ids=("claim_id", lambda x: list(x.dropna())),
    ).reset_index()

    by_target = by_target.merge(totals, on="referring_provider_id")
    by_target["share"] = by_target["count"] / by_target["total"]

    flagged = by_target[by_target["share"] > threshold]

    # Compute peer median (overall median concentration for all providers with enough referrals)
    peer_shares = by_target.groupby("referring_provider_id")["share"].max()
    peer_median = peer_shares.median() if len(peer_shares) > 0 else None

    alerts = []
    for _, row in flagged.iterrows():
        claim_ids = row["claim_ids"] if isinstance(row["claim_ids"], list) else []
        share_pct = round(row["share"] * 100, 1)
        peer_med_pct = round(peer_median * 100, 1) if peer_median is not None else "N/A"

        # Check if rural / single-specialist area
        fp_note = "Check for rural area with limited specialists or employed medical group."
        if providers is not None and "county" in providers.columns:
            target_county = providers.loc[
                providers["provider_id"] == row["target_provider_id"], "county"
            ]
            if not target_county.empty:
                fp_note += f" Target in county: {target_county.values[0]}."

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=claim_ids[:50],  # limit for readability
            fields_matched=["referral_target", "referral_share", "peer_median", "total_referrals"],
            plain_text=(
                f"Provider {row['referring_provider_id']} referred {share_pct}% "
                f"of referrals ({row['count']}/{row['total']}) to {row['target_provider_id']} "
                f"versus peer median {peer_med_pct}%."
            ),
            est_overpay=0,
            severity=severity,
            fp_notes=fp_note,
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=row["referring_provider_id"],
            claim_ids=claim_ids[:50],
            severity=severity,
            est_dollars=0,
            evidence=[ev],
            metadata={
                "target_provider_id": row["target_provider_id"],
                "concentration_share": round(row["share"], 4),
                "referral_count": int(row["count"]),
                "total_referrals": int(row["total"]),
                "peer_median_share": round(peer_median, 4) if peer_median else None,
            },
        ))

    return alerts


# ---------- B: Reciprocal referral loop ----------

def _detect_reciprocal_loop(
    referrals: pd.DataFrame,
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag provider pairs with reciprocal referral relationships."""
    min_refs = config.get("reciprocal_min_referrals", 15)
    severity = config.get("severity", Severity.MEDIUM.value)

    df = referrals.copy()

    # Count referrals per direction
    pair_counts = df.groupby(["referring_provider_id", "target_provider_id"]).agg(
        count=("referral_id", "count"),
        claim_ids=("claim_id", lambda x: list(x.dropna())),
    ).reset_index()

    alerts = []
    seen_pairs = set()

    for _, row_a in pair_counts.iterrows():
        a, b = row_a["referring_provider_id"], row_a["target_provider_id"]
        if row_a["count"] < min_refs:
            continue

        pair_key = tuple(sorted([a, b]))
        if pair_key in seen_pairs:
            continue

        # Check reverse direction
        reverse = pair_counts[
            (pair_counts["referring_provider_id"] == b)
            & (pair_counts["target_provider_id"] == a)
        ]
        if reverse.empty or reverse.iloc[0]["count"] < min_refs:
            continue

        seen_pairs.add(pair_key)
        row_b = reverse.iloc[0]
        claim_ids = (row_a["claim_ids"] + row_b["claim_ids"])[:50]

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=claim_ids,
            fields_matched=["referral_loop", "referring_provider_id", "target_provider_id"],
            plain_text=(
                f"Reciprocal referral loop: {a} referred {row_a['count']} patients to {b}, "
                f"and {b} referred {row_b['count']} patients to {a}. "
                f"Minimum threshold: {min_refs} in each direction."
            ),
            est_overpay=0,
            severity=severity,
            fp_notes="Check for legitimate employment or ownership relationships between providers.",
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=a,
            claim_ids=claim_ids,
            severity=severity,
            est_dollars=0,
            evidence=[ev],
            metadata={
                "loop_partner": b,
                "a_to_b_count": int(row_a["count"]),
                "b_to_a_count": int(row_b["count"]),
            },
        ))

    return alerts


# ---------- C: Same-day referral to high-cost lab ----------

def _detect_same_day_lab(
    claims: pd.DataFrame,
    referrals: pd.DataFrame,
    providers: Optional[pd.DataFrame],
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag same-day referrals to high-cost laboratories."""
    lab_specialties = set(
        s.lower() for s in config.get("high_cost_lab_specialties", ["laboratory", "clinical_lab", "pathology"])
    )
    severity = config.get("severity", Severity.MEDIUM.value)

    if providers is None or "specialty" not in providers.columns:
        return []

    # Identify lab providers
    lab_providers = set(
        providers[providers["specialty"].str.lower().isin(lab_specialties)]["provider_id"]
    )
    if not lab_providers:
        return []

    df_ref = referrals.copy()
    df_ref["referral_date"] = pd.to_datetime(df_ref["referral_date"])

    # Find referrals to labs
    lab_refs = df_ref[df_ref["target_provider_id"].isin(lab_providers)].copy()
    if lab_refs.empty:
        return []

    # Find claims on same day as referral by the referred provider
    df_claims = claims.copy()
    df_claims["service_date"] = pd.to_datetime(df_claims["service_date"])

    ref_cols = [c for c in ["referral_id", "referring_provider_id", "target_provider_id", "member_id", "referral_date"] if c in lab_refs.columns]
    merged = lab_refs[ref_cols].merge(
        df_claims[["claim_id", "provider_id", "member_id", "service_date", "paid_amount"]],
        left_on=["target_provider_id", "member_id", "referral_date"],
        right_on=["provider_id", "member_id", "service_date"],
        how="inner",
    )

    if merged.empty:
        return []

    alerts = []
    for (ref_prov, lab_prov), group in merged.groupby(["referring_provider_id", "target_provider_id"]):
        claim_id_col = "claim_id" if "claim_id" in group.columns else ("claim_id_y" if "claim_id_y" in group.columns else None)
        claim_ids = group[claim_id_col].tolist()[:50] if claim_id_col else []
        total_paid = group["paid_amount"].sum()
        count = len(group)

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=claim_ids,
            fields_matched=["referral_date", "service_date", "specialty", "paid_amount"],
            plain_text=(
                f"Provider {ref_prov} made {count} same-day referrals to "
                f"laboratory {lab_prov} with total paid ${total_paid:,.2f}."
            ),
            est_overpay=0,
            severity=severity,
            fp_notes="Same-day lab referrals may be clinically appropriate. Review medical necessity.",
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=ref_prov,
            claim_ids=claim_ids,
            severity=severity,
            est_dollars=total_paid,
            evidence=[ev],
            metadata={
                "lab_provider_id": lab_prov,
                "same_day_count": count,
                "total_paid": round(total_paid, 2),
            },
        ))

    return alerts


# ---------- D: Referral spike ----------

def _detect_referral_spike(
    referrals: pd.DataFrame,
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag providers with z-score >3 referral volume spike."""
    z_threshold = config.get("referral_zscore_threshold", 3.0)
    trailing_days = config.get("referral_spike_trailing_days", 90)
    severity = config.get("severity", Severity.MEDIUM.value)

    df = referrals.copy()
    df["referral_date"] = pd.to_datetime(df["referral_date"])

    # Weekly referral counts per provider
    df["week_start"] = df["referral_date"] - pd.to_timedelta(
        df["referral_date"].dt.dayofweek, unit="D"
    )
    df["week_start"] = df["week_start"].dt.normalize()

    weekly = df.groupby(["referring_provider_id", "week_start"]).agg(
        weekly_referrals=("referral_id", "count"),
    ).reset_index().sort_values(["referring_provider_id", "week_start"])

    trailing_weeks = trailing_days // 7
    alerts = []

    for pid, group in weekly.groupby("referring_provider_id"):
        if len(group) < 4:  # need minimum history
            continue

        vals = group["weekly_referrals"].values
        weeks = group["week_start"].values

        for i in range(trailing_weeks, len(vals)):
            window = vals[max(0, i - trailing_weeks):i]
            if len(window) < 4:
                continue
            mean = np.mean(window)
            std = np.std(window)
            if std == 0:
                continue
            z = (vals[i] - mean) / std
            if z > z_threshold:
                ev = Evidence(
                    evidence_id=Evidence.generate_id(RULE_ID),
                    rule_id=RULE_ID,
                    rule_version=version,
                    claim_ids=[],
                    fields_matched=["weekly_referrals", "z_score", "trailing_mean", "trailing_std"],
                    plain_text=(
                        f"Provider {pid} referral spike: {vals[i]} referrals in week "
                        f"starting {pd.Timestamp(weeks[i]).strftime('%Y-%m-%d')} "
                        f"(z-score {z:.2f}, trailing mean {mean:.1f}, std {std:.1f})."
                    ),
                    est_overpay=0,
                    severity=severity,
                    fp_notes="Check for legitimate changes: new contracts, seasonal demand.",
                )

                alerts.append(Alert(
                    alert_id=Alert.generate_id(RULE_ID),
                    rule_id=RULE_ID,
                    rule_version=version,
                    entity_type="provider",
                    entity_id=pid,
                    claim_ids=[],
                    severity=severity,
                    est_dollars=0,
                    evidence=[ev],
                    metadata={
                        "z_score": round(z, 3),
                        "weekly_referrals": int(vals[i]),
                        "trailing_mean": round(mean, 2),
                        "trailing_std": round(std, 2),
                        "week_start": str(pd.Timestamp(weeks[i]).date()),
                    },
                ))

    return alerts
