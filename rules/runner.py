"""
Rule runner for Vigil-X Network & Behavioral Intelligence subsystem.

Provides:
- run_network_behavior_rules(data) — runs R06-R10
- run_all_rules(data) — runs R01-R10 (when R01-R05 are available)
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional

import pandas as pd

from contracts.alert import Alert
from rules.r06_timing import detect_impossible_timing
from rules.r07_referral import detect_referral_anomaly
from rules.r08_geographic import detect_geographic_anomaly
from rules.r09_identity import detect_shared_identity
from rules.r10_burst import detect_burst


def run_network_behavior_rules(data: Dict[str, pd.DataFrame]) -> List[Alert]:
    """
    Execute all R06-R10 rules and return combined alerts.

    Args:
        data: Dictionary with keys:
            - 'claims': Claims DataFrame
            - 'providers': Providers DataFrame
            - 'members': Members DataFrame
            - 'referrals': Referrals DataFrame
            - 'facilities': Facilities DataFrame (optional)

    Returns:
        List[Alert] from R06-R10
    """
    claims = data.get("claims", pd.DataFrame())
    providers = data.get("providers", pd.DataFrame())
    members = data.get("members", pd.DataFrame())
    referrals = data.get("referrals", pd.DataFrame())
    facilities = data.get("facilities", pd.DataFrame())

    all_alerts: List[Alert] = []

    # R06 — Impossible Timing
    try:
        r06_alerts = detect_impossible_timing(claims, providers)
        all_alerts.extend(r06_alerts)
    except Exception as e:
        print(f"[R06] Error: {e}")

    # R07 — Referral Anomaly
    try:
        r07_alerts = detect_referral_anomaly(claims, referrals, providers)
        all_alerts.extend(r07_alerts)
    except Exception as e:
        print(f"[R07] Error: {e}")

    # R08 — Geographic Anomaly
    try:
        r08_alerts = detect_geographic_anomaly(
            claims, providers, members, referrals, facilities
        )
        all_alerts.extend(r08_alerts)
    except Exception as e:
        print(f"[R08] Error: {e}")

    # R09 — Shared Identity Link
    try:
        r09_alerts = detect_shared_identity(providers)
        all_alerts.extend(r09_alerts)
    except Exception as e:
        print(f"[R09] Error: {e}")

    # R10 — Burst / Spike
    try:
        r10_alerts = detect_burst(claims)
        all_alerts.extend(r10_alerts)
    except Exception as e:
        print(f"[R10] Error: {e}")

    return all_alerts


def run_all_rules(data: Dict[str, pd.DataFrame]) -> List[Alert]:
    """
    Execute all rules R01-R10 and return combined alerts.
    Adapts standard schema columns for R01-R05 claim utilization rules,
    and runs behavioral network rules R06-R10.
    """
    all_alerts: List[Alert] = []

    # Execute R01-R05 via claim utilization runner if available
    try:
        from vigilx.runner import run_claim_utilization_rules
        data_r01 = dict(data)
        if "claims" in data_r01 and not data_r01["claims"].empty:
            claims_adapter = data_r01["claims"].copy()
            if "service_date" in claims_adapter.columns and "service_from" not in claims_adapter.columns:
                claims_adapter["service_from"] = pd.to_datetime(claims_adapter["service_date"])
            if "procedure_code" in claims_adapter.columns and "cpt_code" not in claims_adapter.columns:
                claims_adapter["cpt_code"] = claims_adapter["procedure_code"]
            if "provider_id" in claims_adapter.columns and "billing_provider_id" not in claims_adapter.columns:
                claims_adapter["billing_provider_id"] = claims_adapter["provider_id"]
            if "status" in claims_adapter.columns and "claim_status" not in claims_adapter.columns:
                claims_adapter["claim_status"] = claims_adapter["status"]
            if "modifier" not in claims_adapter.columns:
                claims_adapter["modifier"] = None
            data_r01["claims"] = claims_adapter

        r01_r05 = run_claim_utilization_rules(data_r01)
        all_alerts.extend(r01_r05)
    except Exception as e:
        print(f"[R01-R05] Error running claim utilization rules: {e}")

    # Execute R06-R10 behavioral and network rules
    all_alerts.extend(run_network_behavior_rules(data))

    return all_alerts
