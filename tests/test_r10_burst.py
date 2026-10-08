"""
Tests for R10 — Burst / Spike.

7 tests covering:
1. Genuine 3x spike
2. Below dollar floor
3. Below 3x threshold
4. New provider
5. Seasonal pattern
6. Insufficient history
7. Exact boundary conditions
"""
import pytest
import pandas as pd
import numpy as np
from rules.r10_burst import detect_burst

CONFIG = {
    "enabled": True,
    "version": "1.0.0",
    "spike_multiplier": 3.0,
    "dollar_floor": 5000,
    "trailing_weeks": 12,
    "min_history_weeks": 4,
    "severity": "MEDIUM",
}


def _weekly_claims(provider_id, weeks_data):
    """Build claims from weekly amounts: [(week_start, amount), ...]"""
    claims = []
    c = 0
    for week_start, amount in weeks_data:
        # Create a single claim per week for simplicity
        c += 1
        claims.append({
            "claim_id": f"C{c:06d}",
            "member_id": f"M{c:04d}",
            "provider_id": provider_id,
            "service_date": week_start,
            "paid_amount": amount,
            "facility_id": None,
            "referring_provider_id": None,
            "service_start_ts": f"{week_start} 10:00:00",
            "service_end_ts": f"{week_start} 10:30:00",
            "service_minutes": 30,
            "pos_code": "11",
            "procedure_code": "CPT99213",
            "diagnosis_code": "ICD001",
            "billed_amount": amount * 1.2,
            "allowed_amount": amount * 1.05,
            "status": "paid",
            "claim_type": "professional",
        })
    return pd.DataFrame(claims)


# 1. Genuine 3x spike
def test_genuine_spike():
    """Provider with steady $2000/week then $20000 in one week → alert."""
    weeks = []
    for w in range(16):
        week_start = f"2024-{(w//4)+1:02d}-{(w%4)*7+1:02d}"
        amount = 2000.0  # steady
        weeks.append((week_start, amount))
    # Spike week
    weeks.append(("2024-05-06", 20000.0))
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    assert len(alerts) >= 1
    assert alerts[0].rule_id == "R10"
    assert alerts[0].metadata["ratio"] >= 3.0


# 2. Below dollar floor
def test_below_dollar_floor():
    """Spike but below $5000 → no alert."""
    weeks = []
    for w in range(16):
        week_start = f"2024-{(w//4)+1:02d}-{(w%4)*7+1:02d}"
        weeks.append((week_start, 500.0))  # $500/week
    weeks.append(("2024-05-06", 4000.0))  # 8x but only $4000
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    spike_alerts = [a for a in alerts if a.metadata.get("weekly_dollars", 0) < 5000]
    assert len(spike_alerts) == 0


# 3. Below 3x threshold
def test_below_multiplier():
    """Provider with 2.5x increase → no alert."""
    weeks = []
    for w in range(16):
        week_start = f"2024-{(w//4)+1:02d}-{(w%4)*7+1:02d}"
        weeks.append((week_start, 5000.0))
    weeks.append(("2024-05-06", 12000.0))  # 2.4x
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    # 12000/5000 = 2.4x < 3x → no alert
    spike_12k = [a for a in alerts if a.metadata.get("weekly_dollars", 0) == 12000.0]
    assert len(spike_12k) == 0


# 4. New provider
def test_new_provider():
    """New provider with only 2 weeks history → no alert (min_history_weeks=4)."""
    weeks = [("2024-01-01", 1000.0), ("2024-01-08", 1000.0), ("2024-01-15", 50000.0)]
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    # Not enough history
    assert len(alerts) == 0


# 5. Seasonal pattern
def test_seasonal_stable():
    """Provider with steady high amounts should not trigger (no spike)."""
    weeks = [(f"2024-{(w//4)+1:02d}-{(w%4)*7+1:02d}", 10000.0) for w in range(20)]
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    # All weeks are same amount → ratio = 1.0 → no alert
    assert len(alerts) == 0


# 6. Insufficient history
def test_insufficient_history():
    """Provider with 3 weeks → insufficient for alerting."""
    weeks = [
        ("2024-01-01", 3000.0),
        ("2024-01-08", 3000.0),
        ("2024-01-15", 3000.0),
        ("2024-01-22", 30000.0),
    ]
    claims = _weekly_claims("P001", weeks)
    config = {**CONFIG, "min_history_weeks": 4}
    alerts = detect_burst(claims, config=config)
    # history_weeks at position 3 is only 3 (weeks 0,1,2) → not enough
    assert len(alerts) == 0


# 7. Exact boundary conditions
def test_boundary_exact_3x():
    """Exactly 3.0x should NOT trigger (threshold is >3x)."""
    weeks = []
    for w in range(16):
        week_start = f"2024-{(w//4)+1:02d}-{(w%4)*7+1:02d}"
        weeks.append((week_start, 5000.0))
    # Exactly 3.0x = $15,000
    weeks.append(("2024-05-06", 15000.0))
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    # ratio = 15000/5000 = 3.0, threshold is >3.0, so should not trigger
    exact_3x = [a for a in alerts if abs(a.metadata.get("ratio", 0) - 3.0) < 0.01]
    assert len(exact_3x) == 0


def test_just_above_3x():
    """3.01x should trigger."""
    weeks = []
    for w in range(16):
        week_start = f"2024-{(w//4)+1:02d}-{(w%4)*7+1:02d}"
        weeks.append((week_start, 5000.0))
    weeks.append(("2024-05-06", 15100.0))  # 3.02x
    claims = _weekly_claims("P001", weeks)
    alerts = detect_burst(claims, config=CONFIG)
    just_over = [a for a in alerts if a.metadata.get("ratio", 0) > 3.0]
    assert len(just_over) >= 1
