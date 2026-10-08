"""
Tests for R06 — Impossible Timing.

8 tests covering:
1. >16-hour provider day
2. Normal provider day
3. Impossible travel
4. Feasible travel
5. Overlapping in-person services
6. Telehealth overlap excluded
7. Missing location handled safely
8. Zero/negative time gap handled safely
"""
import pytest
import pandas as pd
from contracts.alert import Alert
from rules.r06_timing import detect_impossible_timing

# Shared config for tests
CONFIG = {
    "enabled": True,
    "version": "1.0.0",
    "provider_daily_max_minutes": 960,
    "travel_speed_threshold_mph": 60,
    "member_overlap_tolerance_minutes": 0,
    "telehealth_pos_codes": ["02", "10"],
    "severity": "HIGH",
}


def _make_claims(rows):
    """Helper to build a claims DataFrame."""
    defaults = {
        "claim_id": "C001", "member_id": "M001", "provider_id": "P001",
        "facility_id": None, "referring_provider_id": None,
        "service_date": "2024-01-15",
        "service_start_ts": "2024-01-15 08:00:00",
        "service_end_ts": "2024-01-15 09:00:00",
        "service_minutes": 60, "pos_code": "11",
        "procedure_code": "CPT99213", "diagnosis_code": "ICD001",
        "paid_amount": 100.0, "billed_amount": 120.0, "allowed_amount": 105.0,
        "status": "paid", "claim_type": "professional",
        "latitude": 33.75, "longitude": -84.39,
    }
    data = []
    for i, overrides in enumerate(rows):
        row = {**defaults, "claim_id": f"C{i+1:04d}", **overrides}
        data.append(row)
    return pd.DataFrame(data)


def _make_providers(rows):
    defaults = {"provider_id": "P001", "latitude": 33.75, "longitude": -84.39, "specialty": "family_medicine"}
    data = []
    for overrides in rows:
        row = {**defaults, **overrides}
        data.append(row)
    return pd.DataFrame(data)


# 1. >16-hour provider day
def test_overload_detected():
    """Provider billing >16 hours in a day should trigger alert."""
    rows = []
    for h in range(18):  # 18 hours = 1080 minutes
        rows.append({
            "provider_id": "P001",
            "service_date": "2024-01-15",
            "service_start_ts": f"2024-01-15 {6+h:02d}:00:00",
            "service_minutes": 60,
            "pos_code": "11",
        })
    claims = _make_claims(rows)
    alerts = detect_impossible_timing(claims, config=CONFIG)
    overload_alerts = [a for a in alerts if "hours" in a.evidence[0].plain_text and "exceed" in a.evidence[0].plain_text]
    assert len(overload_alerts) >= 1
    assert overload_alerts[0].severity == "HIGH"
    assert overload_alerts[0].rule_id == "R06"


# 2. Normal provider day
def test_normal_day_no_alert():
    """Provider with 8 hours should NOT trigger overload."""
    rows = []
    for h in range(8):
        rows.append({
            "provider_id": "P001",
            "service_date": "2024-01-15",
            "service_start_ts": f"2024-01-15 {8+h:02d}:00:00",
            "service_minutes": 60,
            "pos_code": "11",
        })
    claims = _make_claims(rows)
    alerts = detect_impossible_timing(claims, config=CONFIG)
    overload_alerts = [a for a in alerts if "exceed" in a.evidence[0].plain_text]
    assert len(overload_alerts) == 0


# 3. Impossible travel
def test_impossible_travel_detected():
    """Two services 200 miles apart with 15-minute gap → flag."""
    claims = _make_claims([
        {"claim_id": "C001", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00",
         "latitude": 33.0, "longitude": -84.0, "pos_code": "11", "service_minutes": 15},
        {"claim_id": "C002", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:15:00",
         "latitude": 36.0, "longitude": -84.0, "pos_code": "11", "service_minutes": 15},
    ])
    providers = _make_providers([
        {"provider_id": "P001", "latitude": 33.0, "longitude": -84.0}
    ])
    alerts = detect_impossible_timing(claims, providers, config=CONFIG)
    travel_alerts = [a for a in alerts if "mph" in a.evidence[0].plain_text]
    assert len(travel_alerts) >= 1


# 4. Feasible travel
def test_feasible_travel_no_alert():
    """Two services nearby → no alert."""
    claims = _make_claims([
        {"claim_id": "C001", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00",
         "latitude": 33.75, "longitude": -84.39, "pos_code": "11", "service_minutes": 30},
        {"claim_id": "C002", "provider_id": "P001",
         "service_start_ts": "2024-01-15 10:00:00",
         "latitude": 33.76, "longitude": -84.38, "pos_code": "11", "service_minutes": 30},
    ])
    alerts = detect_impossible_timing(claims, config=CONFIG)
    travel_alerts = [a for a in alerts if "mph" in a.evidence[0].plain_text]
    assert len(travel_alerts) == 0


# 5. Overlapping in-person services
def test_member_overlap_detected():
    """Same member, overlapping services at different providers → alert."""
    claims = _make_claims([
        {"claim_id": "C001", "member_id": "M001", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00", "service_minutes": 60, "pos_code": "11"},
        {"claim_id": "C002", "member_id": "M001", "provider_id": "P002",
         "service_start_ts": "2024-01-15 09:30:00", "service_minutes": 60, "pos_code": "11"},
    ])
    alerts = detect_impossible_timing(claims, config=CONFIG)
    overlap_alerts = [a for a in alerts if "overlapping" in a.evidence[0].plain_text.lower()]
    assert len(overlap_alerts) >= 1


# 6. Telehealth overlap excluded
def test_telehealth_overlap_excluded():
    """Telehealth (POS 02) overlap should NOT trigger."""
    claims = _make_claims([
        {"claim_id": "C001", "member_id": "M001", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00", "service_minutes": 60, "pos_code": "02"},
        {"claim_id": "C002", "member_id": "M001", "provider_id": "P002",
         "service_start_ts": "2024-01-15 09:30:00", "service_minutes": 60, "pos_code": "02"},
    ])
    alerts = detect_impossible_timing(claims, config=CONFIG)
    overlap_alerts = [a for a in alerts if a.entity_type == "member"]
    assert len(overlap_alerts) == 0


# 7. Missing location handled safely
def test_missing_location_safe():
    """Claims without lat/lon should not crash or produce false alerts."""
    claims = _make_claims([
        {"claim_id": "C001", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00", "pos_code": "11", "service_minutes": 30},
        {"claim_id": "C002", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:15:00", "pos_code": "11", "service_minutes": 30},
    ])
    # Remove lat/lon
    claims = claims.drop(columns=["latitude", "longitude"], errors="ignore")
    # Should not crash
    alerts = detect_impossible_timing(claims, config=CONFIG)
    # May or may not produce alerts, but should not crash


# 8. Zero/negative time gap handled safely
def test_zero_time_gap_safe():
    """Zero time gap between services should not crash."""
    claims = _make_claims([
        {"claim_id": "C001", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00",
         "latitude": 33.0, "longitude": -84.0, "pos_code": "11", "service_minutes": 30},
        {"claim_id": "C002", "provider_id": "P001",
         "service_start_ts": "2024-01-15 09:00:00",
         "latitude": 34.0, "longitude": -84.0, "pos_code": "11", "service_minutes": 30},
    ])
    # Should not crash or produce infinite speed
    alerts = detect_impossible_timing(claims, config=CONFIG)
    for a in alerts:
        if "speed" in a.evidence[0].plain_text.lower():
            speed = a.metadata.get("required_speed_mph", 0)
            assert speed != float("inf")
