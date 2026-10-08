"""
Synthetic data generator for Vigil-X.

Generates realistic healthcare claims data with planted FWA patterns
for testing and evaluation. Ground truth is stored separately and
NEVER used for detection.

Target scale:
- 1,200 providers, 25,000 members, 110 facilities
- ~150,000 claims over 24 months
- 5-8 planted fraud rings
"""
from __future__ import annotations

import hashlib
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Reproducibility
SEED = 42

SPECIALTIES = [
    "family_medicine", "internal_medicine", "cardiology", "orthopedics",
    "dermatology", "ophthalmology", "neurology", "psychiatry",
    "laboratory", "radiology", "physical_therapy", "chiropractic",
    "general_surgery", "urology", "pulmonology", "pain_management",
]

FACILITY_TYPES = [
    "clinic", "hospital", "lab", "nursing", "imaging_center",
    "surgery_center", "rehab_center",
]

POS_CODES = ["11", "22", "23", "31", "02", "10"]  # 02, 10 = telehealth

COUNTIES = [
    "Adams", "Baker", "Clark", "Douglas", "Edwards",
    "Franklin", "Grant", "Harrison", "Irving", "Jackson",
    "Kennedy", "Lincoln", "Monroe", "Nelson", "Owens",
]

CITIES = [f"City_{c}" for c in COUNTIES]


def _hash(val: str) -> str:
    """Create a consistent hash for banking/TIN."""
    return hashlib.sha256(val.encode()).hexdigest()[:16]


def generate_synthetic_data(
    n_providers: int = 1200,
    n_members: int = 25000,
    n_facilities: int = 110,
    n_months: int = 24,
    n_claims: Optional[int] = None,
    seed: int = SEED,
    output_dir: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Generate complete synthetic dataset with planted FWA scenarios.

    Returns dict of DataFrames:
    - providers, members, facilities, claims, referrals
    - gt_scenarios, gt_claim_labels, gt_entity_labels
    """
    rng = np.random.RandomState(seed)
    random.seed(seed)

    start_date = datetime(2023, 1, 1)
    end_date = start_date + timedelta(days=n_months * 30)

    # ========== PROVIDERS ==========
    providers = []
    for i in range(n_providers):
        pid = f"P{i+1:04d}"
        county_idx = i % len(COUNTIES)
        base_lat = 33.0 + (county_idx % 5) * 0.5 + rng.normal(0, 0.05)
        base_lon = -84.0 + (county_idx // 5) * 0.5 + rng.normal(0, 0.05)
        specialty = SPECIALTIES[i % len(SPECIALTIES)]
        owner = f"Dr. Owner_{i // 10}"
        bank = f"BANK_{i // 20}"

        providers.append({
            "provider_id": pid,
            "npi": f"NPI{i+1:010d}",
            "name": f"Dr. Provider_{i+1}",
            "specialty": specialty,
            "latitude": round(base_lat, 6),
            "longitude": round(base_lon, 6),
            "address": f"{100 + i} Main St",
            "suite": f"Suite {i % 50}" if i % 3 == 0 else None,
            "city": CITIES[county_idx],
            "state": "GA",
            "zip": f"3{county_idx:04d}",
            "county": COUNTIES[county_idx],
            "facility_type": "clinic",
            "owner_name": owner,
            "owner_entity": f"MedGroup_{i // 30}",
            "registered_agent": f"Agent_{i // 40}" if i % 5 == 0 else None,
            "bank_hash": _hash(bank),
            "tin_hash": _hash(f"TIN_{i // 15}"),
            "group_id": f"GRP_{i // 30}" if i % 4 == 0 else None,
            "enrolled_date": (start_date - timedelta(days=rng.randint(100, 1000))).strftime("%Y-%m-%d"),
        })

    providers_df = pd.DataFrame(providers)

    # ========== MEMBERS ==========
    members = []
    for i in range(n_members):
        mid = f"M{i+1:06d}"
        county_idx = i % len(COUNTIES)
        members.append({
            "member_id": mid,
            "name": f"Patient_{i+1}",
            "dob": f"{1940 + rng.randint(0, 60)}-{rng.randint(1,13):02d}-{rng.randint(1,29):02d}",
            "gender": rng.choice(["M", "F"]),
            "latitude": round(33.0 + (county_idx % 5) * 0.5 + rng.normal(0, 0.1), 6),
            "longitude": round(-84.0 + (county_idx // 5) * 0.5 + rng.normal(0, 0.1), 6),
            "address": f"{200 + i} Oak Ave",
            "city": CITIES[county_idx],
            "state": "GA",
            "zip": f"3{county_idx:04d}",
            "county": COUNTIES[county_idx],
            "plan_type": rng.choice(["HMO", "PPO", "Medicare"]),
            "enrolled_date": (start_date - timedelta(days=rng.randint(30, 730))).strftime("%Y-%m-%d"),
        })

    members_df = pd.DataFrame(members)

    # ========== FACILITIES ==========
    facilities = []
    for i in range(n_facilities):
        fid = f"F{i+1:04d}"
        county_idx = i % len(COUNTIES)
        ftype = FACILITY_TYPES[i % len(FACILITY_TYPES)]
        facilities.append({
            "facility_id": fid,
            "name": f"Facility_{i+1}",
            "facility_type": ftype,
            "latitude": round(33.0 + (county_idx % 5) * 0.5 + rng.normal(0, 0.03), 6),
            "longitude": round(-84.0 + (county_idx // 5) * 0.5 + rng.normal(0, 0.03), 6),
            "address": f"{300 + i} Hospital Dr",
            "suite": None,
            "city": CITIES[county_idx],
            "state": "GA",
            "zip": f"3{county_idx:04d}",
            "county": COUNTIES[county_idx],
            "owner_name": f"HealthCorp_{i // 10}",
            "owner_entity": f"HealthCorp_{i // 10} LLC",
            "capacity": rng.randint(10, 500),
        })

    # Plant suspicious facility types
    facilities[100 % n_facilities]["facility_type"] = "residential"
    facilities[101 % n_facilities]["facility_type"] = "virtual_office"

    facilities_df = pd.DataFrame(facilities)

    # ========== CLAIMS ==========
    claims = []
    claim_counter = 0
    n_days = (end_date - start_date).days

    if n_claims is None:
        n_claims = max(2000, int(150000 * (n_providers / 1200) * (n_months / 24)))

    member_last_end = {}

    for _ in range(n_claims):
        claim_counter += 1
        cid = f"C{claim_counter:07d}"
        pid = f"P{rng.randint(1, n_providers + 1):04d}"
        mid = f"M{rng.randint(1, n_members + 1):06d}"
        fid = f"F{rng.randint(1, n_facilities + 1):04d}" if rng.random() > 0.3 else None

        day_offset = rng.randint(0, n_days)
        svc_date = start_date + timedelta(days=int(day_offset))
        date_str = svc_date.strftime("%Y-%m-%d")

        svc_minutes = int(rng.choice([15, 30, 45, 60]))
        # Avoid overlapping appointments for the same member on the same day in baseline data
        last_end = member_last_end.get((mid, date_str))
        if last_end is not None:
            svc_start = last_end + timedelta(minutes=int(rng.randint(60, 180)))
        else:
            hour = rng.randint(8, 14)
            minute = int(rng.choice([0, 15, 30, 45]))
            svc_start = svc_date.replace(hour=hour, minute=minute)

        svc_end = svc_start + timedelta(minutes=svc_minutes)
        member_last_end[(mid, date_str)] = svc_end

        paid = round(rng.lognormal(4.5, 1.0), 2)
        billed = round(paid * rng.uniform(1.1, 1.5), 2)

        pos = rng.choice(POS_CODES)
        ref_pid = None
        if rng.random() < 0.15:
            ref_pid = f"P{rng.randint(1, n_providers + 1):04d}"

        claims.append({
            "claim_id": cid,
            "member_id": mid,
            "provider_id": pid,
            "facility_id": fid,
            "referring_provider_id": ref_pid,
            "service_date": svc_date.strftime("%Y-%m-%d"),
            "service_start_ts": svc_start.strftime("%Y-%m-%d %H:%M:%S"),
            "service_end_ts": svc_end.strftime("%Y-%m-%d %H:%M:%S"),
            "service_minutes": svc_minutes,
            "pos_code": pos,
            "procedure_code": f"CPT{rng.randint(10000, 99999)}",
            "diagnosis_code": f"ICD{rng.randint(1, 999):03d}",
            "paid_amount": paid,
            "billed_amount": billed,
            "allowed_amount": round(paid * 1.05, 2),
            "status": "paid",
            "claim_type": rng.choice(["professional", "institutional"]),
        })

    claims_df = pd.DataFrame(claims)

    # ========== REFERRALS ==========
    referrals = []
    ref_counter = 0
    ref_claims = claims_df[claims_df["referring_provider_id"].notna()].copy()
    for _, row in ref_claims.iterrows():
        ref_counter += 1
        referrals.append({
            "referral_id": f"REF{ref_counter:07d}",
            "referring_provider_id": row["referring_provider_id"],
            "target_provider_id": row["provider_id"],
            "member_id": row["member_id"],
            "referral_date": row["service_date"],
            "claim_id": row["claim_id"],
        })

    referrals_df = pd.DataFrame(referrals)

    # ========== PLANTED FWA SCENARIOS ==========
    gt_scenarios = []
    gt_claim_labels = []
    gt_entity_labels = []

    # --- Ring 1: Impossible timing ring (R06) ---
    ring1_providers = ["P0001", "P0002", "P0003"]
    gt_scenarios.append({
        "scenario_id": "S001", "scenario_type": "impossible_timing",
        "description": "Ring of providers billing impossible hours and travel",
        "ring_id": "RING_01", "provider_ids": ",".join(ring1_providers),
        "expected_rules": "R06",
    })
    # Plant: P0001 bills 20 hours in one day
    overload_date = "2023-06-15"
    for h in range(20):
        claim_counter += 1
        cid = f"C{claim_counter:07d}"
        mid = f"M{rng.randint(1, 100):06d}"
        claims.append({
            "claim_id": cid, "member_id": mid, "provider_id": "P0001",
            "facility_id": "F0001", "referring_provider_id": None,
            "service_date": overload_date,
            "service_start_ts": f"{overload_date} {7+h:02d}:00:00",
            "service_end_ts": f"{overload_date} {7+h:02d}:55:00",
            "service_minutes": 55, "pos_code": "11",
            "procedure_code": "CPT99213", "diagnosis_code": "ICD001",
            "paid_amount": 150.0, "billed_amount": 200.0, "allowed_amount": 160.0,
            "status": "paid", "claim_type": "professional",
        })
        gt_claim_labels.append({"claim_id": cid, "scenario_id": "S001",
                                "is_suspicious": 1, "label_reason": "impossible_overload"})

    # Plant: P0002 impossible travel (far apart, close in time)
    for k in range(5):
        claim_counter += 1
        cid1 = f"C{claim_counter:07d}"
        claim_counter += 1
        cid2 = f"C{claim_counter:07d}"
        travel_date = f"2023-07-{10+k:02d}"
        mid = f"M{rng.randint(100, 200):06d}"
        claims.append({
            "claim_id": cid1, "member_id": mid, "provider_id": "P0002",
            "facility_id": None, "referring_provider_id": None,
            "service_date": travel_date,
            "service_start_ts": f"{travel_date} 09:00:00",
            "service_end_ts": f"{travel_date} 09:30:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT99213", "diagnosis_code": "ICD002",
            "paid_amount": 200.0, "billed_amount": 250.0, "allowed_amount": 210.0,
            "status": "paid", "claim_type": "professional",
        })
        # Second claim 15 min later, 100 miles away
        claims.append({
            "claim_id": cid2, "member_id": mid, "provider_id": "P0002",
            "facility_id": None, "referring_provider_id": None,
            "service_date": travel_date,
            "service_start_ts": f"{travel_date} 09:15:00",
            "service_end_ts": f"{travel_date} 09:45:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT99214", "diagnosis_code": "ICD002",
            "paid_amount": 200.0, "billed_amount": 250.0, "allowed_amount": 210.0,
            "status": "paid", "claim_type": "professional",
        })
        gt_claim_labels.extend([
            {"claim_id": cid1, "scenario_id": "S001", "is_suspicious": 1, "label_reason": "impossible_travel"},
            {"claim_id": cid2, "scenario_id": "S001", "is_suspicious": 1, "label_reason": "impossible_travel"},
        ])

    # Make P0002 have two very different locations for travel detection
    p2_idx = providers_df.index[providers_df["provider_id"] == "P0002"]
    if len(p2_idx) > 0:
        providers_df.loc[p2_idx[0], "latitude"] = 33.0
        providers_df.loc[p2_idx[0], "longitude"] = -84.0

    for pid in ring1_providers:
        gt_entity_labels.append({
            "entity_type": "provider", "entity_id": pid,
            "scenario_id": "S001", "is_suspicious": 1,
            "label_reason": "impossible_timing_ring"
        })

    # --- Ring 2: Referral fraud ring (R07) ---
    ring2_hub = "P0010"
    ring2_targets = ["P0011", "P0012"]
    gt_scenarios.append({
        "scenario_id": "S002", "scenario_type": "referral_fraud",
        "description": "Hub provider funnels referrals to co-conspirators",
        "ring_id": "RING_02",
        "provider_ids": ",".join([ring2_hub] + ring2_targets),
        "expected_rules": "R07",
    })
    # Plant concentrated referrals: P0010 → P0011 (80 of 100 referrals)
    for k in range(100):
        ref_counter += 1
        target = "P0011" if k < 80 else "P0012"
        ref_date = (start_date + timedelta(days=rng.randint(0, 400))).strftime("%Y-%m-%d")
        mid = f"M{rng.randint(200, 400):06d}"
        claim_counter += 1
        cid = f"C{claim_counter:07d}"
        referrals.append({
            "referral_id": f"REF{ref_counter:07d}",
            "referring_provider_id": ring2_hub,
            "target_provider_id": target,
            "member_id": mid,
            "referral_date": ref_date,
            "claim_id": cid,
        })
        claims.append({
            "claim_id": cid, "member_id": mid, "provider_id": target,
            "facility_id": None, "referring_provider_id": ring2_hub,
            "service_date": ref_date,
            "service_start_ts": f"{ref_date} 10:00:00",
            "service_end_ts": f"{ref_date} 10:30:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT80053", "diagnosis_code": "ICD010",
            "paid_amount": 500.0, "billed_amount": 600.0, "allowed_amount": 520.0,
            "status": "paid", "claim_type": "professional",
        })
        gt_claim_labels.append({"claim_id": cid, "scenario_id": "S002",
                                "is_suspicious": 1, "label_reason": "referral_concentration"})

    # Plant reciprocal: P0011 → P0010 (20 refs)
    for k in range(20):
        ref_counter += 1
        ref_date = (start_date + timedelta(days=rng.randint(0, 400))).strftime("%Y-%m-%d")
        mid = f"M{rng.randint(400, 600):06d}"
        claim_counter += 1
        cid = f"C{claim_counter:07d}"
        referrals.append({
            "referral_id": f"REF{ref_counter:07d}",
            "referring_provider_id": "P0011",
            "target_provider_id": ring2_hub,
            "member_id": mid,
            "referral_date": ref_date,
            "claim_id": cid,
        })
        claims.append({
            "claim_id": cid, "member_id": mid, "provider_id": ring2_hub,
            "facility_id": None, "referring_provider_id": "P0011",
            "service_date": ref_date,
            "service_start_ts": f"{ref_date} 14:00:00",
            "service_end_ts": f"{ref_date} 14:30:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT99213", "diagnosis_code": "ICD011",
            "paid_amount": 200.0, "billed_amount": 250.0, "allowed_amount": 210.0,
            "status": "paid", "claim_type": "professional",
        })

    for pid in [ring2_hub] + ring2_targets:
        gt_entity_labels.append({
            "entity_type": "provider", "entity_id": pid,
            "scenario_id": "S002", "is_suspicious": 1,
            "label_reason": "referral_fraud_ring"
        })

    # Set P0011 specialty to laboratory
    p11_idx = providers_df.index[providers_df["provider_id"] == "P0011"]
    if len(p11_idx) > 0:
        providers_df.loc[p11_idx[0], "specialty"] = "laboratory"

    # --- Ring 3: Identity fraud ring (R09) ---
    ring3_providers = ["P0020", "P0021", "P0022", "P0023"]
    gt_scenarios.append({
        "scenario_id": "S003", "scenario_type": "identity_fraud",
        "description": "Providers sharing bank accounts and ownership",
        "ring_id": "RING_03",
        "provider_ids": ",".join(ring3_providers),
        "expected_rules": "R09",
    })
    shared_bank = _hash("FRAUD_BANK_001")
    shared_owner = "Dr. Fraud Owner Alpha"
    for pid in ring3_providers:
        idx = providers_df.index[providers_df["provider_id"] == pid]
        if len(idx) > 0:
            providers_df.loc[idx[0], "bank_hash"] = shared_bank
            providers_df.loc[idx[0], "owner_name"] = shared_owner
            providers_df.loc[idx[0], "address"] = "999 Conspiracy Lane"
            providers_df.loc[idx[0], "suite"] = "Suite 100"
            providers_df.loc[idx[0], "group_id"] = None  # NOT a documented group
        gt_entity_labels.append({
            "entity_type": "provider", "entity_id": pid,
            "scenario_id": "S003", "is_suspicious": 1,
            "label_reason": "shared_identity_ring"
        })

    # --- Ring 4: Burst/spike ring (R10) ---
    ring4_providers = ["P0030", "P0031"]
    gt_scenarios.append({
        "scenario_id": "S004", "scenario_type": "payment_spike",
        "description": "Providers with sudden billing spikes",
        "ring_id": "RING_04",
        "provider_ids": ",".join(ring4_providers),
        "expected_rules": "R10",
    })
    # Plant: P0030 has normal billing then a huge spike in one week
    spike_week_start = datetime(2024, 3, 4)
    for d in range(7):
        for _ in range(15):
            claim_counter += 1
            cid = f"C{claim_counter:07d}"
            svc_date = (spike_week_start + timedelta(days=d)).strftime("%Y-%m-%d")
            mid = f"M{rng.randint(600, 800):06d}"
            claims.append({
                "claim_id": cid, "member_id": mid, "provider_id": "P0030",
                "facility_id": None, "referring_provider_id": None,
                "service_date": svc_date,
                "service_start_ts": f"{svc_date} {rng.randint(8,17):02d}:00:00",
                "service_end_ts": f"{svc_date} {rng.randint(8,17):02d}:30:00",
                "service_minutes": 30, "pos_code": "11",
                "procedure_code": "CPT99215", "diagnosis_code": "ICD030",
                "paid_amount": 800.0, "billed_amount": 1000.0, "allowed_amount": 850.0,
                "status": "paid", "claim_type": "professional",
            })
            gt_claim_labels.append({"claim_id": cid, "scenario_id": "S004",
                                    "is_suspicious": 1, "label_reason": "payment_spike"})

    for pid in ring4_providers:
        gt_entity_labels.append({
            "entity_type": "provider", "entity_id": pid,
            "scenario_id": "S004", "is_suspicious": 1,
            "label_reason": "payment_spike_ring"
        })

    # --- Ring 5: Geographic anomaly ring (R08) ---
    ring5_providers = ["P0040", "P0041"]
    gt_scenarios.append({
        "scenario_id": "S005", "scenario_type": "geographic_anomaly",
        "description": "Provider serving distant members with no referral",
        "ring_id": "RING_05",
        "provider_ids": ",".join(ring5_providers),
        "expected_rules": "R08",
    })
    # Plant: P0040 at lat 33, serving members at lat 36 (>200 mi)
    p40_idx = providers_df.index[providers_df["provider_id"] == "P0040"]
    if len(p40_idx) > 0:
        providers_df.loc[p40_idx[0], "latitude"] = 33.0
        providers_df.loc[p40_idx[0], "longitude"] = -84.0

    for k in range(50):
        claim_counter += 1
        cid = f"C{claim_counter:07d}"
        mid = f"M{rng.randint(800, 900):06d}"
        # Move this member far away
        m_idx = members_df.index[members_df["member_id"] == mid]
        if len(m_idx) > 0:
            members_df.loc[m_idx[0], "latitude"] = 36.0
            members_df.loc[m_idx[0], "longitude"] = -84.0
        svc_date = (start_date + timedelta(days=rng.randint(0, 500))).strftime("%Y-%m-%d")
        claims.append({
            "claim_id": cid, "member_id": mid, "provider_id": "P0040",
            "facility_id": None, "referring_provider_id": None,
            "service_date": svc_date,
            "service_start_ts": f"{svc_date} 10:00:00",
            "service_end_ts": f"{svc_date} 10:30:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT99213", "diagnosis_code": "ICD040",
            "paid_amount": 150.0, "billed_amount": 200.0, "allowed_amount": 160.0,
            "status": "paid", "claim_type": "professional",
        })
        gt_claim_labels.append({"claim_id": cid, "scenario_id": "S005",
                                "is_suspicious": 1, "label_reason": "geographic_anomaly"})

    for pid in ring5_providers:
        gt_entity_labels.append({
            "entity_type": "provider", "entity_id": pid,
            "scenario_id": "S005", "is_suspicious": 1,
            "label_reason": "geographic_anomaly_ring"
        })

    # --- Ring 6: Stealth ring (R09 + R07 + R10 combined — for ring recovery eval) ---
    ring6_providers = ["P0050", "P0051", "P0052", "P0053", "P0054"]
    gt_scenarios.append({
        "scenario_id": "S006", "scenario_type": "stealth_ring",
        "description": "Coordinated ring: shared identity + referral funneling + billing spikes",
        "ring_id": "RING_06",
        "provider_ids": ",".join(ring6_providers),
        "expected_rules": "R07,R09,R10",
    })
    stealth_bank = _hash("STEALTH_BANK_999")
    stealth_owner = "Stealth Medical Holdings LLC"
    for pid in ring6_providers:
        idx = providers_df.index[providers_df["provider_id"] == pid]
        if len(idx) > 0:
            providers_df.loc[idx[0], "bank_hash"] = stealth_bank
            providers_df.loc[idx[0], "owner_name"] = stealth_owner
            providers_df.loc[idx[0], "registered_agent"] = "Agent Stealth"
            providers_df.loc[idx[0], "group_id"] = None
        gt_entity_labels.append({
            "entity_type": "provider", "entity_id": pid,
            "scenario_id": "S006", "is_suspicious": 1,
            "label_reason": "stealth_ring"
        })

    # Plant referral funneling within stealth ring
    for k in range(40):
        ref_counter += 1
        src = rng.choice(ring6_providers[:3])
        tgt = rng.choice(ring6_providers[3:])
        ref_date = (start_date + timedelta(days=rng.randint(0, 500))).strftime("%Y-%m-%d")
        mid = f"M{rng.randint(900, 1100):06d}"
        claim_counter += 1
        cid = f"C{claim_counter:07d}"
        referrals.append({
            "referral_id": f"REF{ref_counter:07d}",
            "referring_provider_id": src,
            "target_provider_id": tgt,
            "member_id": mid,
            "referral_date": ref_date,
            "claim_id": cid,
        })
        claims.append({
            "claim_id": cid, "member_id": mid, "provider_id": tgt,
            "facility_id": None, "referring_provider_id": src,
            "service_date": ref_date,
            "service_start_ts": f"{ref_date} 11:00:00",
            "service_end_ts": f"{ref_date} 11:30:00",
            "service_minutes": 30, "pos_code": "11",
            "procedure_code": "CPT99214", "diagnosis_code": "ICD050",
            "paid_amount": 400.0, "billed_amount": 500.0, "allowed_amount": 420.0,
            "status": "paid", "claim_type": "professional",
        })

    # Rebuild DataFrames with planted data
    claims_df = pd.DataFrame(claims)
    referrals_df = pd.DataFrame(referrals)
    gt_scenarios_df = pd.DataFrame(gt_scenarios)
    gt_claim_labels_df = pd.DataFrame(gt_claim_labels)
    gt_entity_labels_df = pd.DataFrame(gt_entity_labels)

    data = {
        "providers": providers_df,
        "members": members_df,
        "facilities": facilities_df,
        "claims": claims_df,
        "referrals": referrals_df,
        "gt_scenarios": gt_scenarios_df,
        "gt_claim_labels": gt_claim_labels_df,
        "gt_entity_labels": gt_entity_labels_df,
    }

    # Save to disk if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for name, df in data.items():
            df.to_parquet(os.path.join(output_dir, f"{name}.parquet"), index=False)

    return data
