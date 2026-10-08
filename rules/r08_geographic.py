"""
R08 — Geographic Anomaly

Detects three geographic patterns:
A. Member-to-provider distance exceeds specialty p99 or >75 mi for routine care
B. Provider serves members across 5+ counties
C. Facility at residential/virtual-office address

Uses haversine distance. Accounts for referral justifications.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from contracts.alert import Alert, Evidence, Severity
from config.loader import get_rule_config
from geo.haversine import haversine_distance

RULE_ID = "R08"


def detect_geographic_anomaly(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    members: pd.DataFrame,
    referrals: Optional[pd.DataFrame] = None,
    facilities: Optional[pd.DataFrame] = None,
    config: Optional[Dict] = None,
) -> List[Alert]:
    """Run all R08 sub-rules and return alerts."""
    if config is None:
        config = get_rule_config("R08")

    if not config.get("enabled", True):
        return []

    version = config.get("version", "1.0.0")
    alerts: List[Alert] = []

    if claims is not None and not claims.empty:
        alerts.extend(_detect_distance_anomaly(claims, providers, members, referrals, config, version))
        alerts.extend(_detect_multi_county(claims, members, providers, config, version))

    if facilities is not None and not facilities.empty:
        alerts.extend(_detect_facility_type(facilities, config, version))

    return alerts


# ---------- A: Distance anomaly ----------

def _detect_distance_anomaly(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    members: pd.DataFrame,
    referrals: Optional[pd.DataFrame],
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag member-provider pairs with excessive distance."""
    if claims.empty or providers.empty or members.empty:
        return []

    max_routine_dist = config.get("routine_care_distance_miles", 75)
    default_specialty_dist = config.get("specialty_distance_miles", 150)
    use_p99 = config.get("use_specialty_p99", True)
    telehealth_pos = config.get("telehealth_pos_codes", ["02", "10"])

    ROUTINE_SPECIALTIES = {
        "family_medicine", "internal_medicine", "general_practice",
        "pediatrics", "general_dentistry", "pcp", "primary_care",
    }

    # Exclude telehealth claims
    df = claims.copy()
    if "pos_code" in df.columns:
        df = df[~df["pos_code"].astype(str).isin(telehealth_pos)]
    if df.empty:
        return []

    # Build member-provider distance table
    cols_to_keep = [c for c in ["claim_id", "member_id", "provider_id", "referring_provider_id"] if c in df.columns]
    df = df[cols_to_keep].copy()
    if "referring_provider_id" not in df.columns:
        df["referring_provider_id"] = None

    # Merge member coords
    mem_cols = ["member_id"]
    if "latitude" in members.columns and "longitude" in members.columns:
        mem_cols.extend(["latitude", "longitude"])
    else:
        return []
    df = df.merge(
        members[mem_cols],
        on="member_id", how="left",
    )
    if "latitude" in df.columns and "longitude" in df.columns:
        df = df.rename(columns={"latitude": "mem_lat", "longitude": "mem_lon"})
    else:
        return []

    # Merge provider coords and specialty
    prov_cols = ["provider_id"]
    if "latitude" in providers.columns and "longitude" in providers.columns:
        prov_cols.extend(["latitude", "longitude"])
    else:
        return []
    if "specialty" in providers.columns:
        prov_cols.append("specialty")
    if "county" in providers.columns:
        prov_cols.append("county")

    df = df.merge(
        providers[prov_cols],
        on="provider_id", how="left",
    )
    if "latitude" in df.columns and "longitude" in df.columns:
        df = df.rename(columns={"latitude": "prov_lat", "longitude": "prov_lon"})
    else:
        return []

    # Calculate distances
    df["distance_miles"] = haversine_distance(
        df["mem_lat"], df["mem_lon"], df["prov_lat"], df["prov_lon"]
    )

    # Drop rows without valid distance
    df = df.dropna(subset=["distance_miles"])

    if df.empty:
        return []

    # Compute specialty-specific p99 thresholds ONLY when sample size >= 20 and for non-routine
    specialty_p99 = {}
    if use_p99 and "specialty" in df.columns:
        for spec, spec_grp in df.groupby("specialty"):
            spec_lower = str(spec).lower()
            if spec_lower not in ROUTINE_SPECIALTIES and len(spec_grp) >= 20:
                specialty_p99[spec_lower] = spec_grp["distance_miles"].quantile(0.99)

    # Determine threshold per row
    def _get_threshold(row):
        spec = str(row.get("specialty", "")).lower()
        if spec in ROUTINE_SPECIALTIES:
            return max_routine_dist
        if use_p99 and spec in specialty_p99:
            return max(specialty_p99[spec], default_specialty_dist)
        return default_specialty_dist

    df["threshold"] = df.apply(_get_threshold, axis=1)

    # Flag exceeding threshold
    flagged = df[df["distance_miles"] > df["threshold"]].copy()

    # Check if referral explains the distance
    if referrals is not None and not referrals.empty:
        referred_pairs = set(
            zip(referrals["member_id"], referrals["target_provider_id"])
        )
        flagged["has_referral"] = flagged.apply(
            lambda r: (r["member_id"], r["provider_id"]) in referred_pairs, axis=1
        )
        # Don't fully suppress — just note it
    else:
        flagged["has_referral"] = False

    # Aggregate per provider (group flagged claims)
    alerts = []
    sev_distance = config.get("severity_distance", Severity.MEDIUM.value)

    for pid, group in flagged.groupby("provider_id"):
        claim_ids = group["claim_id"].tolist()[:50]
        avg_dist = group["distance_miles"].mean()
        max_dist = group["distance_miles"].max()
        n_flagged = len(group)
        has_any_referral = group["has_referral"].any()
        specialty = group.get("specialty", pd.Series()).iloc[0] if "specialty" in group.columns else "unknown"
        threshold = group["threshold"].iloc[0]

        fp_notes = "Check for specialty referral centers, snowbirds, or rural care."
        if has_any_referral:
            fp_notes += " Some visits have referrals that may explain the distance."

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=claim_ids,
            fields_matched=["distance_miles", "specialty", "peer_p99", "referral"],
            plain_text=(
                f"Provider {pid} (specialty: {specialty}) has {n_flagged} claims "
                f"with excessive member distance. Avg: {avg_dist:.1f} mi, "
                f"Max: {max_dist:.1f} mi. Threshold: {threshold:.1f} mi."
            ),
            est_overpay=0,
            severity=sev_distance,
            fp_notes=fp_notes,
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=pid,
            claim_ids=claim_ids,
            severity=sev_distance,
            est_dollars=0,
            evidence=[ev],
            metadata={
                "avg_distance_miles": round(avg_dist, 2),
                "max_distance_miles": round(max_dist, 2),
                "flagged_claims": n_flagged,
                "has_referral": has_any_referral,
                "specialty": specialty,
                "threshold_miles": round(threshold, 2),
            },
        ))

    return alerts


# ---------- B: Multi-county provider ----------

def _detect_multi_county(
    claims: pd.DataFrame,
    members: pd.DataFrame,
    providers: pd.DataFrame,
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag providers serving members across 5+ counties."""
    county_threshold = config.get("county_threshold", 5)
    severity = config.get("severity_county", Severity.LOW.value)

    if "county" not in members.columns:
        return []

    df = claims[["claim_id", "member_id", "provider_id"]].merge(
        members[["member_id", "county"]], on="member_id", how="left"
    )
    df = df.dropna(subset=["county"])

    county_counts = (
        df.groupby("provider_id")
        .agg(
            n_counties=("county", "nunique"),
            counties=("county", lambda x: sorted(x.unique().tolist())),
            claim_ids=("claim_id", list),
        )
        .reset_index()
    )

    flagged = county_counts[county_counts["n_counties"] >= county_threshold]

    alerts = []
    for _, row in flagged.iterrows():
        claim_ids = row["claim_ids"][:50]
        counties_str = ", ".join(row["counties"][:10])

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=claim_ids,
            fields_matched=["county", "n_counties", "provider_id"],
            plain_text=(
                f"Provider {row['provider_id']} serves members across "
                f"{row['n_counties']} counties: {counties_str}."
            ),
            est_overpay=0,
            severity=severity,
            fp_notes="May be legitimate for specialists, mobile providers, or telehealth.",
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=row["provider_id"],
            claim_ids=claim_ids,
            severity=severity,
            est_dollars=0,
            evidence=[ev],
            metadata={
                "n_counties": int(row["n_counties"]),
                "counties": row["counties"],
            },
        ))

    return alerts


# ---------- C: Suspicious facility type ----------

def _detect_facility_type(
    facilities: pd.DataFrame,
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag facilities at residential or virtual-office addresses."""
    suspicious_types = set(
        t.lower() for t in config.get("suspicious_facility_types",
                                      ["residential", "virtual_office", "po_box"])
    )
    severity = config.get("severity_facility", Severity.MEDIUM.value)

    if "facility_type" not in facilities.columns:
        return []

    flagged = facilities[
        facilities["facility_type"].str.lower().isin(suspicious_types)
    ].copy()

    alerts = []
    for _, row in flagged.iterrows():
        fid = row["facility_id"]
        ftype = row["facility_type"]
        addr = row.get("address", "unknown")

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=[],
            fields_matched=["facility_type", "address", "facility_id"],
            plain_text=(
                f"Facility {fid} is listed as '{ftype}' at address: {addr}. "
                f"This is inconsistent with expected facility behavior."
            ),
            est_overpay=0,
            severity=severity,
            fp_notes="Verify facility type. Some home-health providers legitimately use residential addresses.",
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="facility",
            entity_id=fid,
            claim_ids=[],
            severity=severity,
            est_dollars=0,
            evidence=[ev],
            metadata={
                "facility_type": ftype,
                "address": addr,
            },
        ))

    return alerts
