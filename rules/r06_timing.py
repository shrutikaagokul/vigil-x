"""
R06 — Impossible Timing

Detects three temporal impossibility patterns:
A. Provider service-day overload (>16 hours)
B. Impossible travel between in-person services (>60 mph required)
C. Member overlapping in-person services at different sites

Telehealth (POS 02, 10) is excluded from travel/overlap checks.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from contracts.alert import Alert, Evidence, Severity
from config.loader import get_rule_config
from geo.haversine import haversine_distance, required_travel_speed

RULE_ID = "R06"


def detect_impossible_timing(
    claims: pd.DataFrame,
    providers: Optional[pd.DataFrame] = None,
    config: Optional[Dict] = None,
) -> List[Alert]:
    """
    Run all R06 sub-rules and return alerts.

    Args:
        claims: Claims DataFrame
        providers: Providers DataFrame (for location data)
        config: R06 config dict

    Returns:
        List[Alert]
    """
    if config is None:
        config = get_rule_config("R06")

    if not config.get("enabled", True):
        return []

    version = config.get("version", "1.0.0")
    alerts: List[Alert] = []

    alerts.extend(_detect_overload(claims, config, version))
    alerts.extend(_detect_impossible_travel(claims, providers, config, version))
    alerts.extend(_detect_member_overlap(claims, config, version))

    return alerts


# ---------- A: Provider service-day overload ----------

def _detect_overload(
    claims: pd.DataFrame,
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag providers whose daily service minutes exceed threshold."""
    max_minutes = config.get("provider_daily_max_minutes", 960)
    severity = config.get("severity", Severity.HIGH.value)

    df = claims.copy()
    df["service_date"] = pd.to_datetime(df["service_date"])
    df["service_minutes"] = pd.to_numeric(df["service_minutes"], errors="coerce").fillna(0)

    daily = (
        df.groupby(["provider_id", "service_date"])
        .agg(
            daily_minutes=("service_minutes", "sum"),
            claim_ids=("claim_id", list),
        )
        .reset_index()
    )

    flagged = daily[daily["daily_minutes"] > max_minutes]
    alerts = []

    for _, row in flagged.iterrows():
        claim_ids = row["claim_ids"]
        daily_hrs = round(row["daily_minutes"] / 60, 1)
        threshold_hrs = max_minutes / 60

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=claim_ids,
            fields_matched=["service_minutes", "service_date", "provider_id"],
            plain_text=(
                f"Provider {row['provider_id']} billed {daily_hrs} hours of services "
                f"on {row['service_date'].strftime('%Y-%m-%d')}, "
                f"exceeding the {threshold_hrs}-hour daily threshold."
            ),
            est_overpay=0,
            severity=severity,
            fp_notes="Check for group-practice shared NPI or legitimate extended procedures.",
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
            fp_notes="May be legitimate for group-practice shared NPI.",
        ))

    return alerts


# ---------- B: Impossible travel ----------

def _detect_impossible_travel(
    claims: pd.DataFrame,
    providers: Optional[pd.DataFrame],
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag consecutive in-person services requiring impossible travel speed."""
    speed_threshold = config.get("travel_speed_threshold_mph", 60)
    telehealth_pos = set(str(c) for c in config.get("telehealth_pos_codes", ["02", "10"]))
    severity = config.get("severity", Severity.HIGH.value)

    df = claims.copy()
    df["service_start_ts"] = pd.to_datetime(df["service_start_ts"], errors="coerce")
    df["pos_code"] = df["pos_code"].astype(str).str.strip()

    # Exclude telehealth
    in_person = df[~df["pos_code"].isin(telehealth_pos)].copy()

    # Need location data — try facility coords first, fall back to provider coords
    if "latitude" not in in_person.columns or "longitude" not in in_person.columns:
        if providers is not None and "latitude" in providers.columns:
            in_person = in_person.merge(
                providers[["provider_id", "latitude", "longitude"]],
                on="provider_id", how="left", suffixes=("", "_prov"),
            )
            if "latitude_prov" in in_person.columns:
                in_person["latitude"] = in_person["latitude"].fillna(in_person["latitude_prov"])
                in_person["longitude"] = in_person["longitude"].fillna(in_person["longitude_prov"])

    # Need lat/lon columns to proceed
    if "latitude" not in in_person.columns or "longitude" not in in_person.columns:
        return []

    # Drop rows without timestamps or coordinates
    in_person = in_person.dropna(subset=["service_start_ts", "latitude", "longitude"])
    if in_person.empty:
        return []

    # Sort by provider and timestamp
    in_person = in_person.sort_values(["provider_id", "service_start_ts"])

    alerts = []

    for pid, group in in_person.groupby("provider_id"):
        if len(group) < 2:
            continue

        rows = group.reset_index(drop=True)
        for i in range(len(rows) - 1):
            r1, r2 = rows.iloc[i], rows.iloc[i + 1]

            # Time gap in hours
            time_gap = (r2["service_start_ts"] - r1["service_start_ts"]).total_seconds() / 3600
            if time_gap <= 0:
                continue  # zero/negative gap — cannot compute, skip safely

            # Distance
            dist = haversine_distance(
                r1["latitude"], r1["longitude"],
                r2["latitude"], r2["longitude"],
            )
            if dist is None or (isinstance(dist, float) and np.isnan(dist)):
                continue

            speed = required_travel_speed(dist, time_gap)
            if speed is None:
                continue

            if speed > speed_threshold:
                claim_ids = [r1["claim_id"], r2["claim_id"]]
                ev = Evidence(
                    evidence_id=Evidence.generate_id(RULE_ID),
                    rule_id=RULE_ID,
                    rule_version=version,
                    claim_ids=claim_ids,
                    fields_matched=[
                        "service_start_ts", "latitude", "longitude",
                        "haversine_distance", "required_speed", "pos_code",
                    ],
                    plain_text=(
                        f"Provider {pid} had consecutive in-person services "
                        f"requiring {speed:.0f} mph travel speed "
                        f"({dist:.1f} mi in {time_gap * 60:.0f} min). "
                        f"Threshold: {speed_threshold} mph. "
                        f"Service 1: {r1['service_start_ts']} at ({r1['latitude']:.4f}, {r1['longitude']:.4f}), "
                        f"POS {r1['pos_code']}. "
                        f"Service 2: {r2['service_start_ts']} at ({r2['latitude']:.4f}, {r2['longitude']:.4f}), "
                        f"POS {r2['pos_code']}."
                    ),
                    est_overpay=0,
                    severity=severity,
                    fp_notes="Verify locations are correct. Check for data-entry timestamp errors.",
                )

                alerts.append(Alert(
                    alert_id=Alert.generate_id(RULE_ID),
                    rule_id=RULE_ID,
                    rule_version=version,
                    entity_type="provider",
                    entity_id=pid,
                    claim_ids=claim_ids,
                    severity=severity,
                    est_dollars=0,
                    evidence=[ev],
                    metadata={
                        "distance_miles": round(dist, 2),
                        "time_gap_hours": round(time_gap, 4),
                        "required_speed_mph": round(speed, 1),
                    },
                ))

    return alerts


# ---------- C: Member overlapping in-person services ----------

def _detect_member_overlap(
    claims: pd.DataFrame,
    config: Dict,
    version: str,
) -> List[Alert]:
    """Flag members with overlapping in-person services at different sites."""
    telehealth_pos = set(str(c) for c in config.get("telehealth_pos_codes", ["02", "10"]))
    severity = config.get("severity", Severity.HIGH.value)

    df = claims.copy()
    df["service_start_ts"] = pd.to_datetime(df["service_start_ts"], errors="coerce")
    df["service_minutes"] = pd.to_numeric(df["service_minutes"], errors="coerce").fillna(0)
    df["pos_code"] = df["pos_code"].astype(str).str.strip()

    # Only in-person services
    in_person = df[~df["pos_code"].isin(telehealth_pos)].copy()
    in_person = in_person.dropna(subset=["service_start_ts"])

    if in_person.empty:
        return []

    # Calculate service end time
    in_person["service_end_ts"] = (
        in_person["service_start_ts"]
        + pd.to_timedelta(in_person["service_minutes"], unit="m")
    )

    # Sort by member and start time
    in_person = in_person.sort_values(["member_id", "service_start_ts"])

    alerts = []

    for mid, group in in_person.groupby("member_id"):
        if len(group) < 2:
            continue

        rows = group.reset_index(drop=True)
        for i in range(len(rows) - 1):
            r1, r2 = rows.iloc[i], rows.iloc[i + 1]

            # Check for overlap: service1 ends after service2 starts
            if r1["service_end_ts"] <= r2["service_start_ts"]:
                continue

            # Must be different providers or facilities to be suspicious
            same_provider = r1["provider_id"] == r2["provider_id"]
            same_facility = (
                pd.notna(r1.get("facility_id")) and pd.notna(r2.get("facility_id"))
                and r1.get("facility_id") == r2.get("facility_id")
            )
            if same_provider or same_facility:
                continue  # legitimate — same site

            claim_ids = [r1["claim_id"], r2["claim_id"]]
            overlap_minutes = (r1["service_end_ts"] - r2["service_start_ts"]).total_seconds() / 60

            ev = Evidence(
                evidence_id=Evidence.generate_id(RULE_ID),
                rule_id=RULE_ID,
                rule_version=version,
                claim_ids=claim_ids,
                fields_matched=[
                    "member_id", "service_start_ts", "service_end_ts",
                    "provider_id", "pos_code",
                ],
                plain_text=(
                    f"Member {mid} has overlapping in-person services: "
                    f"Provider {r1['provider_id']} ({r1['service_start_ts']} - {r1['service_end_ts']}, "
                    f"POS {r1['pos_code']}) overlaps with "
                    f"Provider {r2['provider_id']} ({r2['service_start_ts']} - {r2['service_end_ts']}, "
                    f"POS {r2['pos_code']}). "
                    f"Overlap: {overlap_minutes:.0f} minutes."
                ),
                est_overpay=0,
                severity=severity,
                fp_notes="Check for group billing or clock/data-entry errors.",
            )

            alerts.append(Alert(
                alert_id=Alert.generate_id(RULE_ID),
                rule_id=RULE_ID,
                rule_version=version,
                entity_type="member",
                entity_id=mid,
                claim_ids=claim_ids,
                severity=severity,
                est_dollars=0,
                evidence=[ev],
                metadata={
                    "overlap_minutes": round(overlap_minutes, 1),
                    "provider_1": r1["provider_id"],
                    "provider_2": r2["provider_id"],
                },
            ))

    return alerts
