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

    R01-R05 are imported dynamically to allow independent development.
    If R01-R05 are not yet available, only R06-R10 run.
    """
    all_alerts: List[Alert] = []

    # Try R01-R05 (owned by another engineer)
    r01_r05_rules = [
        ("R01", "rules.r01_duplicate", "detect_duplicate_billing"),
        ("R02", "rules.r02_upcoding", "detect_upcoding"),
        ("R03", "rules.r03_unbundling", "detect_unbundling"),
        ("R04", "rules.r04_phantom", "detect_phantom_services"),
        ("R05", "rules.r05_utilization", "detect_excessive_utilization"),
    ]

    for rule_id, module_name, func_name in r01_r05_rules:
        try:
            import importlib
            mod = importlib.import_module(module_name)
            func = getattr(mod, func_name)
            alerts = func(data)
            all_alerts.extend(alerts)
        except (ImportError, ModuleNotFoundError):
            pass  # R01-R05 not yet available
        except Exception as e:
            print(f"[{rule_id}] Error: {e}")

    # R06-R10
    all_alerts.extend(run_network_behavior_rules(data))

    return all_alerts
