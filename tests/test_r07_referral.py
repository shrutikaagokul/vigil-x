"""
Tests for R07 — Referral Anomaly.

8 tests covering:
1. >70% concentration
2. Normal referral distribution
3. Insufficient sample size
4. Reciprocal loop
5. No reciprocal loop
6. Same-day high-cost lab
7. Referral spike
8. Legitimate rural/single-specialist scenario
"""
import pytest
import pandas as pd
from rules.r07_referral import detect_referral_anomaly

CONFIG = {
    "enabled": True,
    "version": "1.0.0",
    "concentration_threshold": 0.70,
    "min_referral_count": 20,
    "reciprocal_min_referrals": 15,
    "high_cost_lab_specialties": ["laboratory", "clinical_lab"],
    "referral_zscore_threshold": 3.0,
    "referral_spike_trailing_days": 90,
    "severity": "MEDIUM",
}


def _make_referrals(rows):
    data = []
    for i, overrides in enumerate(rows):
        row = {
            "referral_id": f"REF{i+1:04d}",
            "referring_provider_id": "P001",
            "target_provider_id": "P002",
            "member_id": f"M{i+1:04d}",
            "referral_date": "2024-01-15",
            "claim_id": f"C{i+1:04d}",
            **overrides,
        }
        data.append(row)
    return pd.DataFrame(data)


def _make_claims(rows):
    data = []
    for i, overrides in enumerate(rows):
        row = {
            "claim_id": f"C{i+1:04d}", "member_id": f"M{i+1:04d}",
            "provider_id": "P001", "facility_id": None,
            "referring_provider_id": None,
            "service_date": "2024-01-15",
            "service_start_ts": "2024-01-15 10:00:00",
            "service_end_ts": "2024-01-15 10:30:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT99213", "diagnosis_code": "ICD001",
            "paid_amount": 100.0, "billed_amount": 120.0,
            "allowed_amount": 105.0, "status": "paid",
            "claim_type": "professional",
            **overrides,
        }
        data.append(row)
    return pd.DataFrame(data)


def _make_providers(rows):
    data = []
    for overrides in rows:
        row = {"provider_id": "P001", "specialty": "family_medicine",
               "county": "Adams", **overrides}
        data.append(row)
    return pd.DataFrame(data)


# 1. >70% concentration
def test_concentration_detected():
    """Provider sending >70% of 25 referrals to one target."""
    refs = []
    for i in range(25):
        target = "P002" if i < 20 else "P003"  # 80% to P002
        refs.append({"referring_provider_id": "P001", "target_provider_id": target,
                      "referral_date": f"2024-01-{(i%28)+1:02d}"})
    referrals = _make_referrals(refs)
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, config=CONFIG)
    conc_alerts = [a for a in alerts if "referred" in a.evidence[0].plain_text.lower()
                   and "%" in a.evidence[0].plain_text]
    assert len(conc_alerts) >= 1


# 2. Normal referral distribution
def test_normal_distribution_no_alert():
    """Even distribution across targets should not trigger."""
    refs = []
    for i in range(25):
        target = f"P{(i % 5) + 10:04d}"  # 5 targets, ~5 each = 20%
        refs.append({"referring_provider_id": "P001", "target_provider_id": target,
                      "referral_date": f"2024-01-{(i%28)+1:02d}"})
    referrals = _make_referrals(refs)
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, config=CONFIG)
    conc_alerts = [a for a in alerts if "referred" in a.evidence[0].plain_text.lower()
                   and "%" in a.evidence[0].plain_text]
    assert len(conc_alerts) == 0


# 3. Insufficient sample size
def test_insufficient_sample_no_alert():
    """Provider with <20 referrals should not trigger concentration."""
    refs = [{"referring_provider_id": "P001", "target_provider_id": "P002",
             "referral_date": "2024-01-15"}] * 10  # Only 10
    referrals = _make_referrals(refs)
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, config=CONFIG)
    conc_alerts = [a for a in alerts if "referred" in a.evidence[0].plain_text.lower()
                   and "%" in a.evidence[0].plain_text]
    assert len(conc_alerts) == 0


# 4. Reciprocal loop
def test_reciprocal_loop_detected():
    """A→B with 20 refs AND B→A with 20 refs → loop detected."""
    refs = []
    for i in range(20):
        refs.append({"referring_provider_id": "P001", "target_provider_id": "P002",
                      "referral_date": f"2024-01-{(i%28)+1:02d}"})
    for i in range(20):
        refs.append({"referring_provider_id": "P002", "target_provider_id": "P001",
                      "referral_date": f"2024-02-{(i%28)+1:02d}"})
    referrals = _make_referrals(refs)
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, config=CONFIG)
    loop_alerts = [a for a in alerts if "reciprocal" in a.evidence[0].plain_text.lower()]
    assert len(loop_alerts) >= 1


# 5. No reciprocal loop
def test_no_reciprocal_loop():
    """One-directional referrals should not trigger loop."""
    refs = [{"referring_provider_id": "P001", "target_provider_id": "P002",
             "referral_date": f"2024-01-{(i%28)+1:02d}"} for i in range(25)]
    referrals = _make_referrals(refs)
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, config=CONFIG)
    loop_alerts = [a for a in alerts if "reciprocal" in a.evidence[0].plain_text.lower()]
    assert len(loop_alerts) == 0


# 6. Same-day high-cost lab
def test_same_day_lab():
    """Same-day referral to laboratory should be flagged."""
    providers = _make_providers([
        {"provider_id": "P001", "specialty": "family_medicine"},
        {"provider_id": "P002", "specialty": "laboratory"},
    ])
    refs = []
    claims_list = []
    for i in range(5):
        date = f"2024-03-{i+1:02d}"
        mid = f"M{i+100:04d}"
        refs.append({
            "referring_provider_id": "P001", "target_provider_id": "P002",
            "member_id": mid, "referral_date": date, "claim_id": f"CL{i:04d}",
        })
        claims_list.append({
            "claim_id": f"CL{i:04d}", "member_id": mid,
            "provider_id": "P002", "referring_provider_id": "P001",
            "service_date": date, "paid_amount": 500.0,
        })
    referrals = _make_referrals(refs)
    claims = _make_claims(claims_list)
    alerts = detect_referral_anomaly(claims, referrals, providers, config=CONFIG)
    lab_alerts = [a for a in alerts if "laboratory" in a.evidence[0].plain_text.lower()
                  or "lab" in a.evidence[0].plain_text.lower()]
    assert len(lab_alerts) >= 1


# 7. Referral spike
def test_referral_spike():
    """Sudden burst of referrals should be detected."""
    refs = []
    # Steady 5/week for 20 weeks, then 50 in one week
    for week in range(20):
        for d in range(5):
            date = f"2024-{(week//4)+1:02d}-{(week%4)*7+d+1:02d}"
            refs.append({
                "referring_provider_id": "P001", "target_provider_id": "P005",
                "referral_date": date,
            })
    # Spike week
    for d in range(50):
        refs.append({
            "referring_provider_id": "P001", "target_provider_id": "P005",
            "referral_date": "2024-06-10",
        })
    referrals = _make_referrals(refs)
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, config=CONFIG)
    spike_alerts = [a for a in alerts if "spike" in a.evidence[0].plain_text.lower()
                    or "z-score" in a.evidence[0].plain_text.lower()]
    assert len(spike_alerts) >= 1


# 8. Rural/single-specialist scenario
def test_rural_no_over_flag():
    """High concentration in rural area should still trigger but with FP notes."""
    refs = []
    for i in range(25):
        refs.append({
            "referring_provider_id": "P001", "target_provider_id": "P002",
            "referral_date": f"2024-01-{(i%28)+1:02d}",
        })
    referrals = _make_referrals(refs)
    providers = _make_providers([
        {"provider_id": "P001", "county": "Rural_County"},
        {"provider_id": "P002", "county": "Rural_County"},
    ])
    claims = _make_claims([])
    alerts = detect_referral_anomaly(claims, referrals, providers, config=CONFIG)
    # Should trigger but with rural/specialist FP note
    for a in alerts:
        if "referred" in a.evidence[0].plain_text.lower():
            assert "rural" in a.evidence[0].fp_notes.lower() or "specialist" in a.evidence[0].fp_notes.lower()
