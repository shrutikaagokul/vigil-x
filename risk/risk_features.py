"""
Signal extraction, adaptation, and normalization for the Vigil-X Unified Risk Engine.

This module consumes outputs produced by existing Vigil-X subsystems (R01-R10 rules,
claim ML, provider anomaly, future risk forecasting, network analysis, and temporal features)
and maps them into clean, standardized, provider-level signal components in [0, 1].

DOES NOT modify or re-run existing subsystems; consumes their outputs cleanly.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd


# ------------------------------------------------------------------------------
# Robust Helpers for Safe Numeric Handling
# ------------------------------------------------------------------------------

def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, replacing NaN, inf, and None with default."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def clip_01(val: float) -> float:
    """Clamp a float strictly into [0.0, 1.0]."""
    if math.isnan(val) or math.isinf(val):
        return 0.0
    return max(0.0, min(1.0, float(val)))


# ------------------------------------------------------------------------------
# 1. Rule Signals Adapter (Consumes R01-R10 alerts)
# ------------------------------------------------------------------------------

def extract_rule_signals(
    alerts_data: Optional[Union[List[Any], pd.DataFrame]],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Aggregate existing R01-R10 alert outputs to provider level.
    
    Accepts:
      - List of Alert objects (dataclasses from contracts/alert.py or vigilx/models/alert.py)
      - List of alert dicts
      - pandas DataFrame of alerts
      
    Returns:
      (dict of provider_id -> rule_signals_dict, rules_available_flag)
    """
    if alerts_data is None:
        return {}, False

    norm_cfg = (config or {}).get("normalization", {}).get("rules", {})
    count_cap = norm_cfg.get("alert_count_cap", 10)
    dollars_cap = norm_cfg.get("dollars_cap", 50000.0)
    rules_cap = norm_cfg.get("distinct_rules_cap", 5)
    sev_weights = norm_cfg.get("severity_weights", {
        "LOW": 0.25,
        "MEDIUM": 0.50,
        "HIGH": 0.75,
        "CRITICAL": 1.00,
    })

    # Standardize alerts into a list of dictionaries
    alerts_list: List[Dict[str, Any]] = []
    if isinstance(alerts_data, pd.DataFrame):
        if alerts_data.empty:
            return {}, True
        for _, row in alerts_data.iterrows():
            d = row.to_dict()
            # Normalize entity_id / provider_id
            if "entity_id" not in d and "provider_id" in d:
                d["entity_id"] = d["provider_id"]
            alerts_list.append(d)
    elif isinstance(alerts_data, list):
        for item in alerts_data:
            if hasattr(item, "to_dict"):
                alerts_list.append(item.to_dict())
            elif isinstance(item, dict):
                alerts_list.append(item)
            elif hasattr(item, "entity_id"):
                # Direct dataclass attribute access
                alerts_list.append({
                    "alert_id": getattr(item, "alert_id", ""),
                    "rule_id": getattr(item, "rule_id", ""),
                    "entity_type": getattr(item, "entity_type", "provider"),
                    "entity_id": getattr(item, "entity_id", ""),
                    "severity": getattr(item, "severity", "MEDIUM"),
                    "est_dollars": getattr(item, "est_dollars", 0.0),
                    "evidence": getattr(item, "evidence", []),
                    "claim_ids": getattr(item, "claim_ids", []),
                })
    else:
        return {}, False

    # Group by provider_id
    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    # Identify providers that actually have alerts
    alerts_provider_set: Set[str] = set()
    for alert in alerts_list:
        entity_type = alert.get("entity_type", "provider")
        entity_id = alert.get("entity_id") or alert.get("provider_id")
        if entity_id and (not entity_type or entity_type == "provider"):
            alerts_provider_set.add(str(entity_id))

    # Initialize universe if provided
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "rule_alert_count": 0,
                "high_severity_rule_count": 0,
                "estimated_rule_dollars": 0.0,
                "distinct_rules_triggered": set(),
                "rule_alert_ids": [],
                "rule_evidence_ids": [],
                "rule_claim_ids": set(),
                "severity_score_sum": 0.0,
                "rule_component": 0.0,
                "rules_available": (pid in alerts_provider_set),
            }

    for alert in alerts_list:
        entity_type = alert.get("entity_type", "provider")
        entity_id = alert.get("entity_id") or alert.get("provider_id")
        if not entity_id or (entity_type and entity_type != "provider"):
            continue
        pid = str(entity_id)

        if pid not in prov_grouped:
            prov_grouped[pid] = {
                "rule_alert_count": 0,
                "high_severity_rule_count": 0,
                "estimated_rule_dollars": 0.0,
                "distinct_rules_triggered": set(),
                "rule_alert_ids": [],
                "rule_evidence_ids": [],
                "rule_claim_ids": set(),
                "severity_score_sum": 0.0,
                "rule_component": 0.0,
                "rules_available": True,
            }

        rec = prov_grouped[pid]
        rec["rule_alert_count"] += 1
        rec["rule_alert_ids"].append(str(alert.get("alert_id", "")))

        rule_id = alert.get("rule_id", "")
        if rule_id:
            rec["distinct_rules_triggered"].add(str(rule_id))

        # Severity
        sev = alert.get("severity")
        if hasattr(sev, "value"):
            sev_str = str(sev.value).upper()
        else:
            sev_str = str(sev).upper() if sev else "MEDIUM"
        
        if sev_str in ("HIGH", "CRITICAL"):
            rec["high_severity_rule_count"] += 1
        
        weight = sev_weights.get(sev_str, 0.50)
        rec["severity_score_sum"] += weight

        # Dollars
        rec["estimated_rule_dollars"] += safe_float(alert.get("est_dollars", 0.0))

        # Claims & Evidence references
        claim_ids = alert.get("claim_ids") or []
        rec["rule_claim_ids"].update(str(c) for c in claim_ids)

        ev_list = alert.get("evidence") or []
        for ev in ev_list:
            if isinstance(ev, dict):
                ev_id = ev.get("evidence_id")
                if ev_id:
                    rec["rule_evidence_ids"].append(str(ev_id))
            elif hasattr(ev, "evidence_id"):
                rec["rule_evidence_ids"].append(str(ev.evidence_id))

    # Compute normalized rule_component in [0, 1] for each provider
    for pid, rec in prov_grouped.items():
        cnt = rec["rule_alert_count"]
        if cnt == 0:
            rec["rule_component"] = 0.0
            rec["rule_severity_score"] = 0.0
            rec["rule_claim_ids"] = list(rec["rule_claim_ids"])
            rec["distinct_rules_triggered"] = sorted(list(rec["distinct_rules_triggered"]))
            continue

        count_factor = min(cnt / max(count_cap, 1), 1.0)
        mean_sev = rec["severity_score_sum"] / cnt
        rec["rule_severity_score"] = mean_sev

        distinct_cnt = len(rec["distinct_rules_triggered"])
        breadth_factor = min(distinct_cnt / max(rules_cap, 1), 1.0)

        # Logarithmic financial factor
        dollars = rec["estimated_rule_dollars"]
        dollar_factor = min(math.log1p(max(dollars, 0.0)) / math.log1p(dollars_cap), 1.0)

        # High severity proportion
        high_sev_prop = rec["high_severity_rule_count"] / cnt

        comp = (
            0.30 * count_factor
            + 0.25 * mean_sev
            + 0.20 * high_sev_prop
            + 0.15 * breadth_factor
            + 0.10 * dollar_factor
        )
        rec["rule_component"] = clip_01(comp)
        rec["rule_claim_ids"] = sorted(list(rec["rule_claim_ids"]))
        rec["distinct_rules_triggered"] = sorted(list(rec["distinct_rules_triggered"]))

    return prov_grouped, True


# ------------------------------------------------------------------------------
# 2. ML Signals Adapter (Consumes claim_ml predictions)
# ------------------------------------------------------------------------------

def extract_ml_signals(
    claim_ml_df: Optional[pd.DataFrame],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Aggregate claim-level ML predictions to provider level.
    
    Prefers 'calibrated_probability' if present. Fallback to 'ml_probability' or 'ml_risk_score'.
    Does NOT describe uncalibrated scores as probabilities in human outputs.
    """
    if claim_ml_df is None or claim_ml_df.empty:
        return {}, False

    norm_cfg = (config or {}).get("normalization", {}).get("ml", {})
    threshold = norm_cfg.get("high_risk_threshold", 0.50)
    rate_weight = norm_cfg.get("rate_weight", 0.60)
    prob_weight = norm_cfg.get("prob_weight", 0.40)

    # Determine primary probability column
    has_calibrated = "calibrated_probability" in claim_ml_df.columns
    if has_calibrated:
        prob_col = "calibrated_probability"
    elif "ml_probability" in claim_ml_df.columns:
        prob_col = "ml_probability"
    elif "ml_risk_score" in claim_ml_df.columns:
        prob_col = "ml_risk_score"
    else:
        # No recognized probability column
        return {}, False

    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    # Pre-populate universe if provided
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "high_risk_claim_count": 0,
                "high_risk_claim_rate": 0.0,
                "mean_ml_score": 0.0,
                "max_ml_score": 0.0,
                "high_risk_claim_ids": [],
                "ml_component": 0.0,
                "has_calibrated": has_calibrated,
                "ml_available": False,
            }

    # Group by provider_id
    grouped = claim_ml_df.groupby("provider_id")
    for pid, group in grouped:
        pid_str = str(pid)
        probs = pd.to_numeric(group[prob_col], errors="coerce").fillna(0.0).values
        n_claims = len(probs)
        if n_claims == 0:
            continue

        high_mask = probs >= threshold
        high_cnt = int(np.sum(high_mask))
        high_rate = high_cnt / float(n_claims)
        mean_p = float(np.mean(probs))
        max_p = float(np.max(probs))

        high_ids: List[str] = []
        if "claim_id" in group.columns and high_cnt > 0:
            high_ids = group.loc[high_mask, "claim_id"].astype(str).tolist()

        # Component in [0, 1]
        comp = clip_01(rate_weight * high_rate + prob_weight * mean_p)

        prov_grouped[pid_str] = {
            "high_risk_claim_count": high_cnt,
            "high_risk_claim_rate": round(high_rate, 4),
            "mean_ml_score": round(mean_p, 4),
            "max_ml_score": round(max_p, 4),
            "high_risk_claim_ids": high_ids,
            "ml_component": comp,
            "has_calibrated": has_calibrated,
            "ml_available": True,
        }

    return prov_grouped, True


# ------------------------------------------------------------------------------
# 3. Provider Anomaly Adapter (Consumes Isolation Forest provider_anomaly)
# ------------------------------------------------------------------------------

def extract_anomaly_signals(
    anomaly_df: Optional[pd.DataFrame],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Extract Isolation Forest provider anomaly detection signals.
    
    Unsupervised behavioral anomaly score and percentile rank.
    Not described as fraud probability.
    """
    if anomaly_df is None or anomaly_df.empty:
        return {}, False

    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "anomaly_score": 0.0,
                "anomaly_percentile": 0.0,
                "anomaly_flag": 0,
                "anomaly_component": 0.0,
                "anomaly_available": False,
            }

    for _, row in anomaly_df.iterrows():
        pid = str(row.get("provider_id", ""))
        if not pid:
            continue

        score = safe_float(row.get("anomaly_score", 0.0))
        pct = safe_float(row.get("anomaly_percentile", 0.0))
        flag = int(safe_float(row.get("anomaly_flag", 0)))

        # Normalized component [0, 1] based on percentile rank
        comp = clip_01(pct / 100.0)

        prov_grouped[pid] = {
            "anomaly_score": score,
            "anomaly_percentile": pct,
            "anomaly_flag": flag,
            "anomaly_component": comp,
            "anomaly_available": True,
        }

    return prov_grouped, True


# ------------------------------------------------------------------------------
# 4. Future Risk Adapter (Consumes 30d/60d/90d future_risk forecasts)
# ------------------------------------------------------------------------------

def extract_future_risk_signals(
    future_risk_df: Optional[pd.DataFrame],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Extract forward risk predictions (risk_30d, risk_60d, risk_90d).
    
    Combines horizons using configurable weighted combination.
    """
    if future_risk_df is None or future_risk_df.empty:
        return {}, False

    fut_cfg = (config or {}).get("future_risk", {})
    w_30 = fut_cfg.get("w_30d", 0.50)
    w_60 = fut_cfg.get("w_60d", 0.30)
    w_90 = fut_cfg.get("w_90d", 0.20)
    total_w = w_30 + w_60 + w_90
    if total_w > 0:
        w_30 /= total_w
        w_60 /= total_w
        w_90 /= total_w

    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "risk_30d": 0.0,
                "risk_60d": 0.0,
                "risk_90d": 0.0,
                "future_component": 0.0,
                "future_available": False,
            }

    for _, row in future_risk_df.iterrows():
        pid = str(row.get("provider_id", ""))
        if not pid:
            continue

        r30 = clip_01(safe_float(row.get("risk_30d", 0.0)))
        r60 = clip_01(safe_float(row.get("risk_60d", 0.0)))
        r90 = clip_01(safe_float(row.get("risk_90d", 0.0)))

        comp = clip_01(w_30 * r30 + w_60 * r60 + w_90 * r90)

        prov_grouped[pid] = {
            "risk_30d": r30,
            "risk_60d": r60,
            "risk_90d": r90,
            "future_component": comp,
            "future_available": True,
        }

    return prov_grouped, True


# ------------------------------------------------------------------------------
# 5. Network Signals Adapter (Consumes network & community features)
# ------------------------------------------------------------------------------

def extract_network_signals(
    network_data: Optional[Any],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Extract network risk features at the provider level.
    
    Supports:
      - Provider-level network DataFrame directly
      - Community-level DataFrame with 'communities' list
      - Tuple of (network_features_df, communities_list)
      - Network graph representation
    """
    if network_data is None:
        return {}, False

    norm_cfg = (config or {}).get("normalization", {}).get("network", {})
    hard_link_w = norm_cfg.get("hard_link_weight", 0.35)
    referral_w = norm_cfg.get("referral_weight", 0.25)
    centrality_w = norm_cfg.get("hub_centrality_weight", 0.20)
    size_w = norm_cfg.get("size_weight", 0.20)
    size_cap = norm_cfg.get("size_cap", 15)

    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "community_id": None,
                "community_size": 0,
                "hard_link_score": 0.0,
                "referral_score": 0.0,
                "hub_centrality": 0.0,
                "is_hub": False,
                "network_component": 0.0,
                "network_available": True,  # Network analysis ran; isolated = 0 risk
            }

    # Case A: Tuple of (network_df, communities) or dict with both
    net_df = None
    communities_list = None

    if isinstance(network_data, tuple) and len(network_data) == 2:
        net_df, communities_list = network_data
    elif isinstance(network_data, dict) and "network_features" in network_data:
        net_df = network_data["network_features"]
        communities_list = network_data.get("communities")
    elif isinstance(network_data, pd.DataFrame):
        net_df = network_data
    elif isinstance(network_data, list):
        # List of community dicts directly
        communities_list = network_data

    # Process community list if available
    if communities_list:
        # Build community metadata map
        comm_meta: Dict[int, Dict[str, Any]] = {}
        if isinstance(net_df, pd.DataFrame) and not net_df.empty:
            for _, r in net_df.iterrows():
                cid = int(safe_float(r.get("community_id", -1)))
                comm_meta[cid] = r.to_dict()

        for comm in communities_list:
            if not isinstance(comm, dict):
                continue
            cid = int(safe_float(comm.get("community_id", -1)))
            pids = comm.get("provider_ids", [])
            hub_id = comm.get("hub_provider_id", "")
            hard_links = safe_float(comm.get("hard_link_count", 0))
            n_prov = len(pids)

            # Retrieve community-level scores from net_df if present
            meta = comm_meta.get(cid, {})
            hard_score = safe_float(meta.get("hard_link_score", min(hard_links / max(n_prov, 1), 1.0)))
            ref_score = safe_float(meta.get("referral_score", 0.0))
            hub_cent = safe_float(meta.get("hub_centrality", 0.0))

            size_norm = min(n_prov / max(size_cap, 1), 1.0)
            comp = clip_01(
                hard_link_w * hard_score
                + referral_w * ref_score
                + centrality_w * hub_cent
                + size_w * size_norm
            )

            for pid in pids:
                pid_str = str(pid)
                is_hub = (pid_str == str(hub_id))
                prov_grouped[pid_str] = {
                    "community_id": cid,
                    "community_size": n_prov,
                    "hard_link_score": hard_score,
                    "referral_score": ref_score,
                    "hub_centrality": hub_cent if is_hub else hub_cent * 0.5,
                    "is_hub": is_hub,
                    "network_component": comp,
                    "network_available": True,
                }

    elif isinstance(net_df, pd.DataFrame) and not net_df.empty:
        # Check if net_df is provider-level (contains 'provider_id')
        if "provider_id" in net_df.columns:
            for _, r in net_df.iterrows():
                pid = str(r.get("provider_id", ""))
                if not pid:
                    continue
                cid = int(safe_float(r.get("community_id", -1))) if pd.notna(r.get("community_id")) else None
                hard_score = safe_float(r.get("hard_link_score", 0.0))
                ref_score = safe_float(r.get("referral_score", 0.0))
                hub_cent = safe_float(r.get("hub_centrality", 0.0))
                n_prov = int(safe_float(r.get("n_providers", r.get("community_size", 1))))

                size_norm = min(n_prov / max(size_cap, 1), 1.0)
                comp = clip_01(
                    hard_link_w * hard_score
                    + referral_w * ref_score
                    + centrality_w * hub_cent
                    + size_w * size_norm
                )

                prov_grouped[pid] = {
                    "community_id": cid,
                    "community_size": n_prov,
                    "hard_link_score": hard_score,
                    "referral_score": ref_score,
                    "hub_centrality": hub_cent,
                    "is_hub": bool(r.get("is_hub", False)),
                    "network_component": comp,
                    "network_available": True,
                }

    return prov_grouped, True


# ------------------------------------------------------------------------------
# 6. Temporal / Behavioral Signals Adapter
# ------------------------------------------------------------------------------

def extract_temporal_signals(
    temporal_data: Optional[Any],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Extract temporal signals (billing burst, spike multiplier, volatility).
    """
    if temporal_data is None:
        return {}, False

    norm_cfg = (config or {}).get("normalization", {}).get("temporal", {})
    burst_cap = norm_cfg.get("burst_cv_cap", 3.0)

    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "burst_cv": 0.0,
                "temporal_component": 0.0,
                "temporal_available": False,
            }

    if isinstance(temporal_data, pd.DataFrame) and not temporal_data.empty:
        if "provider_id" in temporal_data.columns:
            for _, r in temporal_data.iterrows():
                pid = str(r.get("provider_id", ""))
                if not pid:
                    continue
                # Support prov_burst_cv or burst_score or spike_multiplier
                cv = safe_float(r.get("prov_burst_cv", r.get("burst_score", 0.0)))
                comp = clip_01(min(cv / max(burst_cap, 1e-4), 1.0))
                prov_grouped[pid] = {
                    "burst_cv": cv,
                    "temporal_component": comp,
                    "temporal_available": True,
                }

    return prov_grouped, True


# ------------------------------------------------------------------------------
# 7. Historical Signals Adapter
# ------------------------------------------------------------------------------

def extract_historical_signals(
    historical_data: Optional[Any],
    provider_universe: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Extract historical provider signals if available.
    Does NOT fabricate historical data if unavailable.
    """
    if historical_data is None:
        return {}, False

    prov_grouped: Dict[str, Dict[str, Any]] = {}
    
    if provider_universe:
        for pid in provider_universe:
            prov_grouped[pid] = {
                "historical_component": 0.0,
                "historical_available": False,
            }

    if isinstance(historical_data, pd.DataFrame) and not historical_data.empty:
        if "provider_id" in historical_data.columns:
            for _, r in historical_data.iterrows():
                pid = str(r.get("provider_id", ""))
                if not pid:
                    continue
                comp = clip_01(safe_float(r.get("historical_risk", r.get("prior_risk_score", 0.0))))
                prov_grouped[pid] = {
                    "historical_component": comp,
                    "historical_available": True,
                }

    return prov_grouped, True
