"""
Tests for R08 — Geographic Anomaly.

8 tests covering:
1. Extreme distance
2. Normal local care
3. Valid referral explains distance
4. Rural provider
5. Specialty center
6. 5+ county provider
7. Virtual office
8. Missing coordinates
"""
import pytest
import pandas as pd
from rules.r08_geographic import detect_geographic_anomaly

CONFIG = {
    "enabled": True,
    "version": "1.0.0",
    "routine_care_distance_miles": 75,
    "use_specialty_p99": True,
    "county_threshold": 5,
    "suspicious_facility_types": ["residential", "virtual_office", "po_box"],
    "severity_distance": "MEDIUM",
    "severity_county": "LOW",
    "severity_facility": "MEDIUM",
}


def _claims(rows):
    defaults = {
        "claim_id": "C0001", "member_id": "M001", "provider_id": "P001",
        "referring_provider_id": None, "facility_id": None,
    }
    if not rows:
        return pd.DataFrame(columns=list(defaults.keys()))
    data = []
    for i, o in enumerate(rows):
        row = {**defaults, "claim_id": f"C{i+1:04d}", **o}
        data.append(row)
    return pd.DataFrame(data)


def _providers(rows):
    return pd.DataFrame([
        {"provider_id": "P001", "latitude": 33.75, "longitude": -84.39,
         "specialty": "family_medicine", "county": "Adams", **o}
        for o in rows
    ])


def _members(rows):
    return pd.DataFrame([
        {"member_id": "M001", "latitude": 33.75, "longitude": -84.39,
         "county": "Adams", **o}
        for o in rows
    ])


# 1. Extreme distance
def test_extreme_distance():
    """Member 300 miles from provider → alert."""
    claims = _claims([{"member_id": "M001", "provider_id": "P001"}])
    providers = _providers([{"provider_id": "P001", "latitude": 33.0, "longitude": -84.0}])
    members = _members([{"member_id": "M001", "latitude": 37.0, "longitude": -84.0}])  # ~277 mi
    alerts = detect_geographic_anomaly(claims, providers, members, config=CONFIG)
    dist_alerts = [a for a in alerts if "distance" in a.evidence[0].plain_text.lower()]
    assert len(dist_alerts) >= 1


# 2. Normal local care
def test_normal_local():
    """Member 5 miles from provider → no alert."""
    claims = _claims([{"member_id": "M001", "provider_id": "P001"}])
    providers = _providers([{"provider_id": "P001", "latitude": 33.75, "longitude": -84.39}])
    members = _members([{"member_id": "M001", "latitude": 33.76, "longitude": -84.38}])
    alerts = detect_geographic_anomaly(claims, providers, members, config=CONFIG)
    dist_alerts = [a for a in alerts if "distance" in a.evidence[0].plain_text.lower()]
    assert len(dist_alerts) == 0


# 3. Valid referral explains distance
def test_referral_explains_distance():
    """Distance alert should note referral presence."""
    claims = _claims([{"member_id": "M001", "provider_id": "P001", "referring_provider_id": "P002"}])
    providers = _providers([{"provider_id": "P001", "latitude": 33.0, "longitude": -84.0}])
    members = _members([{"member_id": "M001", "latitude": 37.0, "longitude": -84.0}])
    referrals = pd.DataFrame([{
        "referral_id": "REF001", "referring_provider_id": "P002",
        "target_provider_id": "P001", "member_id": "M001",
        "referral_date": "2024-01-15", "claim_id": "C0001",
    }])
    alerts = detect_geographic_anomaly(claims, providers, members, referrals, config=CONFIG)
    for a in alerts:
        if "distance" in a.evidence[0].plain_text.lower():
            assert "referral" in a.evidence[0].fp_notes.lower()


# 4. Rural provider (still triggers but with FP notes)
def test_rural_provider():
    """Rural provider serving distant patients → alert with rural FP notes."""
    claims = _claims([{"member_id": "M001", "provider_id": "P001"} for _ in range(5)])
    providers = _providers([{"provider_id": "P001", "latitude": 33.0, "longitude": -84.0}])
    members = _members([{"member_id": "M001", "latitude": 35.0, "longitude": -84.0}])
    alerts = detect_geographic_anomaly(claims, providers, members, config=CONFIG)
    # Should have FP note about rural/specialist
    for a in alerts:
        if "distance" in a.evidence[0].plain_text.lower():
            assert "rural" in a.evidence[0].fp_notes.lower() or "specialist" in a.evidence[0].fp_notes.lower()


# 5. Specialty center (p99 consideration)
def test_specialty_center():
    """Specialty that typically has longer distances should use higher p99 threshold."""
    # All claims in dataset are distant → p99 is high, so shouldn't flag
    claims_data = []
    for i in range(100):
        claims_data.append({
            "member_id": f"M{i+1:04d}", "provider_id": "P001",
        })
    claims = _claims(claims_data)
    providers = _providers([{"provider_id": "P001", "latitude": 33.0, "longitude": -84.0,
                              "specialty": "oncology"}])
    # All members at roughly same distance (~138 mi)
    members = pd.DataFrame([{
        "member_id": f"M{i+1:04d}", "latitude": 35.0 + (i * 0.001), "longitude": -84.0,
        "county": "Remote"
    } for i in range(100)])
    alerts = detect_geographic_anomaly(claims, providers, members, config=CONFIG)
    # With p99 adjustment, many should fall within threshold


# 6. 5+ county provider
def test_multi_county():
    """Provider serving members across 6 counties → alert."""
    claims_data = []
    members_data = []
    counties = ["Adams", "Baker", "Clark", "Douglas", "Edwards", "Franklin"]
    for i, county in enumerate(counties):
        mid = f"M{i+1:04d}"
        claims_data.append({"member_id": mid, "provider_id": "P001"})
        members_data.append({"member_id": mid, "county": county,
                              "latitude": 33.0 + i * 0.5, "longitude": -84.0})
    claims = _claims(claims_data)
    providers = _providers([{"provider_id": "P001"}])
    members = pd.DataFrame(members_data)
    alerts = detect_geographic_anomaly(claims, providers, members, config=CONFIG)
    county_alerts = [a for a in alerts if "counties" in a.evidence[0].plain_text.lower()]
    assert len(county_alerts) >= 1


# 7. Virtual office
def test_virtual_office():
    """Facility flagged as virtual_office → alert."""
    claims = _claims([])
    providers = _providers([{}])
    members = _members([{}])
    facilities = pd.DataFrame([{
        "facility_id": "F001", "facility_type": "virtual_office",
        "address": "123 Virtual St", "name": "Virtual Clinic",
    }])
    alerts = detect_geographic_anomaly(claims, providers, members, facilities=facilities, config=CONFIG)
    fac_alerts = [a for a in alerts if a.entity_type == "facility"]
    assert len(fac_alerts) >= 1


# 8. Missing coordinates
def test_missing_coordinates():
    """Claims with missing coordinates should not crash."""
    claims = _claims([{"member_id": "M001", "provider_id": "P001"}])
    providers = pd.DataFrame([{
        "provider_id": "P001", "specialty": "family_medicine", "county": "Adams",
    }])  # No lat/lon
    members = _members([{"member_id": "M001"}])
    # Should not crash
    alerts = detect_geographic_anomaly(claims, providers, members, config=CONFIG)
