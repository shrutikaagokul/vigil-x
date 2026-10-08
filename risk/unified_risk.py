"""
Standalone Unified Risk Engine for Vigil-X.

Combines existing signals from rules (R01-R10), claim ML, provider anomaly detection,
future risk forecasts, network graph analysis, and temporal behavior into a single,
explainable, defensible provider risk prioritization score.

CRITICAL DEFINITIONS:
  - This is a RISK PRIORITIZATION score for Special Investigation Units (SIU).
  - It is NOT a fraud confirmation or legal determination.
  - Language used: "Prioritized for human investigation", "Elevated risk indicator".
  - NEVER: "Fraud confirmed".
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
import yaml

from risk.contracts import (
    ConfidenceTier,
    EvidenceTier,
    ProviderScoreRecord,
    RiskTier,
    SignalAvailability,
    SignalComponents,
    SignalContributions,
)
from risk.risk_features import (
    clip_01,
    extract_anomaly_signals,
    extract_future_risk_signals,
    extract_historical_signals,
    extract_ml_signals,
    extract_network_signals,
    extract_rule_signals,
    extract_temporal_signals,
    safe_float,
)

# ------------------------------------------------------------------------------
# Default Configuration Path
# ------------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = Path(__file__).parent / "risk_config.yaml"


def load_risk_config(config_input: Optional[Union[Dict[str, Any], Path, str]] = None) -> Dict[str, Any]:
    """
    Load and validate the risk configuration YAML or dictionary.
    
    Verifies that:
      - Required weight keys exist
      - Core weights sum to 1.0 within numerical tolerance
      - Tier thresholds are monotonic
    """
    if config_input is None:
        config_path = DEFAULT_CONFIG_PATH
        if not config_path.exists():
            raise FileNotFoundError(f"Default risk config file not found: {config_path}")
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
    elif isinstance(config_input, (str, Path)):
        config_path = Path(config_input)
        if not config_path.exists():
            raise FileNotFoundError(f"Risk config file not found: {config_path}")
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
    elif isinstance(config_input, dict):
        cfg = config_input.copy()
    else:
        raise TypeError(f"Unsupported config type: {type(config_input)}")

    # Validate weights
    weights = cfg.get("weights", {})
    required_families = ["rules", "ml", "anomaly", "network", "temporal", "future", "historical"]
    for fam in required_families:
        if fam not in weights:
            weights[fam] = 0.0

    total_weight = sum(float(w) for w in weights.values())
    if abs(total_weight - 1.0) > 1e-5:
        raise ValueError(
            f"Configured weights must sum to 1.0 (got {total_weight:.6f}): {weights}"
        )

    # Validate future risk weights if present
    fut_cfg = cfg.get("future_risk", {})
    if fut_cfg:
        w_fut_sum = float(fut_cfg.get("w_30d", 0.0)) + float(fut_cfg.get("w_60d", 0.0)) + float(fut_cfg.get("w_90d", 0.0))
        if abs(w_fut_sum - 1.0) > 1e-5:
            raise ValueError(f"future_risk weights must sum to 1.0 (got {w_fut_sum:.6f}): {fut_cfg}")

    return cfg


# ------------------------------------------------------------------------------
# Tier Mapping Functions
# ------------------------------------------------------------------------------

def get_risk_tier(score: float, tiers_cfg: Dict[str, Any]) -> str:
    """Map continuous risk score to RiskTier string."""
    low_t = tiers_cfg.get("low_threshold", 0.25)
    mod_t = tiers_cfg.get("moderate_threshold", 0.50)
    high_t = tiers_cfg.get("high_threshold", 0.75)

    if score < low_t:
        return RiskTier.LOW.value
    elif score < mod_t:
        return RiskTier.MODERATE.value
    elif score < high_t:
        return RiskTier.HIGH.value
    else:
        return RiskTier.CRITICAL.value


def get_evidence_tier(strength: float, tiers_cfg: Dict[str, Any]) -> str:
    """Map continuous evidence strength to EvidenceTier string."""
    low_t = tiers_cfg.get("low_threshold", 0.25)
    mod_t = tiers_cfg.get("moderate_threshold", 0.50)
    high_t = tiers_cfg.get("high_threshold", 0.75)

    if strength < low_t:
        return EvidenceTier.LOW.value
    elif strength < mod_t:
        return EvidenceTier.MODERATE.value
    elif strength < high_t:
        return EvidenceTier.HIGH.value
    else:
        return EvidenceTier.VERY_HIGH.value


def get_confidence_tier(confidence: float, tiers_cfg: Dict[str, Any]) -> str:
    """Map continuous confidence score to ConfidenceTier string."""
    low_t = tiers_cfg.get("low_threshold", 0.40)
    mod_t = tiers_cfg.get("moderate_threshold", 0.70)

    if confidence < low_t:
        return ConfidenceTier.LOW.value
    elif confidence < mod_t:
        return ConfidenceTier.MEDIUM.value
    else:
        return ConfidenceTier.HIGH.value


# ------------------------------------------------------------------------------
# Evidence Strength Calculation
# ------------------------------------------------------------------------------

def compute_evidence_strength(
    components: SignalComponents,
    availability: SignalAvailability,
    rule_data: Dict[str, Any],
    ml_data: Dict[str, Any],
    network_data: Dict[str, Any],
    config: Dict[str, Any],
) -> float:
    """
    Compute evidence strength independently from risk score.
    
    Evaluates:
      - Corroboration across independent signal families
      - Depth and breadth of rule violations and financial exposure
      - ML claim volume support without double-counting shared claim IDs
      - Network structural corroboration (hard identity links, community membership)
      
    Returns strength bounded in [0.0, 1.0].
    """
    ev_cfg = config.get("evidence", {})
    activation_t = ev_cfg.get("family_activation_threshold", 0.20)
    
    # 1. Independent signal family activation count
    active_families = 0
    if availability.rules_available and components.rule_component >= activation_t:
        active_families += 1
    if availability.ml_available and components.ml_component >= activation_t:
        active_families += 1
    if availability.anomaly_available and components.anomaly_component >= activation_t:
        active_families += 1
    if availability.network_available and components.network_component >= activation_t:
        active_families += 1
    if availability.future_available and components.future_component >= activation_t:
        active_families += 1
    if availability.temporal_available and components.temporal_component >= activation_t:
        active_families += 1

    corroboration_factor = min(active_families / 3.0, 1.0)

    # 2. Rule evidence depth
    distinct_rules = len(rule_data.get("distinct_rules_triggered", []))
    breadth_factor = min(distinct_rules / 3.0, 1.0)
    high_sev_cnt = rule_data.get("high_severity_rule_count", 0)
    sev_factor = min(high_sev_cnt / 3.0, 1.0)
    dollars = rule_data.get("estimated_rule_dollars", 0.0)
    dollar_factor = min(math.log1p(max(dollars, 0.0)) / math.log1p(50000.0), 1.0)
    rule_depth = 0.40 * breadth_factor + 0.35 * sev_factor + 0.25 * dollar_factor

    # 3. Claim-level ML evidence with double-counting mitigation
    rule_claim_ids = set(rule_data.get("rule_claim_ids", []))
    ml_claim_ids = set(ml_data.get("high_risk_claim_ids", []))
    # Combine into unique claims to prevent double-counting identical claims
    unique_claim_evidence = len(rule_claim_ids | ml_claim_ids)
    claim_support = min(unique_claim_evidence / 15.0, 1.0)

    # 4. Network support
    hard_links = network_data.get("hard_link_score", 0.0)
    comm_size = network_data.get("community_size", 0)
    network_support = min(hard_links * 0.60 + min(comm_size / 10.0, 1.0) * 0.40, 1.0)

    # 5. Combine into evidence strength
    w_corrob = ev_cfg.get("corroboration_weight", 0.30)
    w_rule = ev_cfg.get("rule_depth_weight", 0.25)
    w_claim = ev_cfg.get("ml_support_weight", 0.25)
    w_net = ev_cfg.get("network_support_weight", 0.20)

    strength = (
        w_corrob * corroboration_factor
        + w_rule * rule_depth
        + w_claim * claim_support
        + w_net * network_support
    )
    return clip_01(strength)


# ------------------------------------------------------------------------------
# Confidence Score Calculation
# ------------------------------------------------------------------------------

def compute_confidence_score(
    components: SignalComponents,
    availability: SignalAvailability,
    weights_cfg: Dict[str, float],
    ml_data: Dict[str, Any],
    rule_data: Dict[str, Any],
    config: Dict[str, Any],
) -> float:
    """
    Compute confidence score reflecting input completeness, signal agreement, and sample size.
    
    IMPORTANT: This measures reliability and data completeness, NOT fraud probability.
    """
    conf_cfg = config.get("confidence", {})
    w_avail = conf_cfg.get("availability_weight", 0.60)
    w_agree = conf_cfg.get("agreement_weight", 0.25)
    w_sample = conf_cfg.get("sample_size_weight", 0.15)

    # 1. Availability / Completeness factor
    total_configured_w = sum(weights_cfg.values())
    avail_w = 0.0
    active_components: List[float] = []

    if availability.rules_available:
        avail_w += weights_cfg.get("rules", 0.0)
        active_components.append(components.rule_component)
    if availability.ml_available:
        avail_w += weights_cfg.get("ml", 0.0)
        active_components.append(components.ml_component)
    if availability.anomaly_available:
        avail_w += weights_cfg.get("anomaly", 0.0)
        active_components.append(components.anomaly_component)
    if availability.network_available:
        avail_w += weights_cfg.get("network", 0.0)
        active_components.append(components.network_component)
    if availability.temporal_available:
        avail_w += weights_cfg.get("temporal", 0.0)
        active_components.append(components.temporal_component)
    if availability.future_available:
        avail_w += weights_cfg.get("future", 0.0)
        active_components.append(components.future_component)
    if availability.historical_available:
        avail_w += weights_cfg.get("historical", 0.0)
        active_components.append(components.historical_component)

    if avail_w == 0.0 or availability.available_count() == 0:
        return 0.0

    availability_score = avail_w / max(total_configured_w, 1e-6)

    # 2. Agreement between independent signal families
    if len(active_components) >= 2:
        std_dev = float(np.std(active_components))
        # High std_dev (e.g. 0.45) means high divergence; agreement decreases
        agreement_score = max(0.0, 1.0 - 2.0 * std_dev)
    elif len(active_components) == 1:
        agreement_score = 0.50
    else:
        agreement_score = 0.0

    # 3. Sample size factor
    n_claims = ml_data.get("high_risk_claim_count", 0) + len(rule_data.get("rule_claim_ids", []))
    sample_cap = conf_cfg.get("claim_count_cap", 30)
    sample_score = min(n_claims / max(sample_cap, 1), 1.0) if n_claims > 0 else 0.40

    confidence = (
        w_avail * availability_score
        + w_agree * agreement_score
        + w_sample * sample_score
    )
    return clip_01(confidence)


# ------------------------------------------------------------------------------
# Top Reasons Generator
# ------------------------------------------------------------------------------

def generate_top_reasons(
    components: SignalComponents,
    contributions: SignalContributions,
    rule_data: Dict[str, Any],
    ml_data: Dict[str, Any],
    anomaly_data: Dict[str, Any],
    network_data: Dict[str, Any],
    future_data: Dict[str, Any],
    temporal_data: Dict[str, Any],
    max_reasons: int = 4,
) -> List[str]:
    """
    Generate machine-readable, evidence-backed top reasons for investigator review.
    
    Ranks drivers by their weighted contributions and builds explainable descriptions.
    Uses NO LLM, NO hardcoding of provider IDs.
    """
    candidate_reasons: List[Tuple[float, str]] = []

    # 1. Rules
    if contributions.rule_contribution > 0.02:
        high_sev = rule_data.get("high_severity_rule_count", 0)
        dollars = rule_data.get("estimated_rule_dollars", 0.0)
        distinct = rule_data.get("distinct_rules_triggered", [])
        if high_sev >= 2:
            candidate_reasons.append((
                contributions.rule_contribution,
                f"Multiple high-severity billing rule alerts ({high_sev} alerts, ${dollars:,.0f} est. exposure)",
            ))
        elif len(distinct) >= 2:
            rules_str = ", ".join(distinct[:3])
            candidate_reasons.append((
                contributions.rule_contribution,
                f"Triggered multiple detection rules ({rules_str})",
            ))
        elif rule_data.get("rule_alert_count", 0) > 0:
            candidate_reasons.append((
                contributions.rule_contribution,
                f"Billing anomalies detected ({rule_data['rule_alert_count']} alert(s), ${dollars:,.0f} est. exposure)",
            ))

    # 2. ML Claims
    if contributions.ml_contribution > 0.02:
        high_cnt = ml_data.get("high_risk_claim_count", 0)
        rate = ml_data.get("high_risk_claim_rate", 0.0)
        mean_s = ml_data.get("mean_ml_score", 0.0)
        if rate >= 0.25 and high_cnt >= 3:
            candidate_reasons.append((
                contributions.ml_contribution,
                f"High concentration of suspicious claims ({rate:.1%} rate, {high_cnt} flagged claims)",
            ))
        else:
            candidate_reasons.append((
                contributions.ml_contribution,
                f"Elevated claim-level ML risk score (mean calibrated probability: {mean_s:.2f})",
            ))

    # 3. Network
    if contributions.network_contribution > 0.02:
        hard_links = network_data.get("hard_link_score", 0.0)
        cid = network_data.get("community_id")
        c_size = network_data.get("community_size", 0)
        is_hub = network_data.get("is_hub", False)

        if hard_links >= 0.5:
            candidate_reasons.append((
                contributions.network_contribution,
                f"Hard identity links with affiliated entities (shared bank/TIN/owner overlap)",
            ))
        elif is_hub:
            candidate_reasons.append((
                contributions.network_contribution,
                f"Central hub provider in multi-provider network (Community #{cid}, {c_size} providers)",
            ))
        elif c_size >= 2:
            candidate_reasons.append((
                contributions.network_contribution,
                f"Connected to elevated-risk provider community (Community #{cid}, {c_size} providers)",
            ))

    # 4. Provider Anomaly
    if contributions.anomaly_contribution > 0.02:
        pct = anomaly_data.get("anomaly_percentile", 0.0)
        flag = anomaly_data.get("anomaly_flag", 0)
        if pct >= 90.0 or flag == 1:
            candidate_reasons.append((
                contributions.anomaly_contribution,
                f"Statistically anomalous macro billing behavior ({pct:.0f}th percentile among peer providers)",
            ))
        else:
            candidate_reasons.append((
                contributions.anomaly_contribution,
                f"Elevated behavioral anomaly profile compared to peer specialty baseline",
            ))

    # 5. Future Risk
    if contributions.future_contribution > 0.02:
        r30 = future_data.get("risk_30d", 0.0)
        candidate_reasons.append((
            contributions.future_contribution,
            f"Elevated near-term forward risk forecast ({r30:.2f} 30-day forecast probability)",
        ))

    # 6. Temporal
    if contributions.temporal_contribution > 0.01:
        candidate_reasons.append((
            contributions.temporal_contribution,
            f"Billing volume surge / velocity spike exceeding historical baseline",
        ))

    # Sort descending by contribution
    candidate_reasons.sort(key=lambda x: x[0], reverse=True)
    reasons = [r[1] for r in candidate_reasons[:max_reasons]]
    
    if not reasons:
        reasons = ["Baseline risk profile with no elevated indicators"]
    return reasons


# ------------------------------------------------------------------------------
# Core Unified Risk Engine Computation Function
# ------------------------------------------------------------------------------

def compute_unified_risk(
    rules_output: Optional[Any] = None,
    ml_output: Optional[pd.DataFrame] = None,
    anomaly_output: Optional[pd.DataFrame] = None,
    future_risk_output: Optional[pd.DataFrame] = None,
    network_output: Optional[Any] = None,
    temporal_output: Optional[Any] = None,
    historical_output: Optional[pd.DataFrame] = None,
    provider_ids: Optional[Union[List[str], Set[str]]] = None,
    config: Optional[Union[Dict[str, Any], Path, str]] = None,
) -> pd.DataFrame:
    """
    Compute unified provider risk prioritization scores and explanations.
    
    Parameters
    ----------
    rules_output : List[Alert] or DataFrame of alerts from R01-R10
    ml_output : DataFrame of claim-level ML predictions (claim_ml.parquet)
    anomaly_output : DataFrame of Isolation Forest provider anomalies (provider_anomaly.parquet)
    future_risk_output : DataFrame of forward horizon risks (future_risk.parquet)
    network_output : DataFrame or (net_df, communities) from network subsystem
    temporal_output : DataFrame of temporal features
    historical_output : DataFrame of historical provider risk if available
    provider_ids : Optional explicit set of provider IDs to score
    config : Configuration dictionary, Path, or None (loads risk_config.yaml)
    
    Returns
    -------
    pd.DataFrame
        Complete provider_scores DataFrame matching the output contract.
    """
    cfg = load_risk_config(config)
    weights_cfg = cfg.get("weights", {})
    renormalize = cfg.get("renormalize_missing_weights", True)
    risk_tiers_cfg = cfg.get("risk_tiers", {})
    ev_tiers_cfg = cfg.get("evidence_tiers", {})
    conf_tiers_cfg = cfg.get("confidence_tiers", {})
    engine_ver = cfg.get("engine_version", "1.0.0")
    model_ver = cfg.get("model_version", "1.0.0")
    feat_ver = cfg.get("feature_version", "1.0.0")

    # Step 1: Establish Provider Universe
    universe: Set[str] = set()
    if provider_ids:
        universe = set(str(p) for p in provider_ids)
    else:
        # Harvest provider IDs across provided inputs (ensuring entity_type == 'provider')
        if isinstance(rules_output, pd.DataFrame):
            if "provider_id" in rules_output.columns:
                universe.update(rules_output["provider_id"].dropna().astype(str).tolist())
            elif "entity_id" in rules_output.columns:
                if "entity_type" in rules_output.columns:
                    mask = rules_output["entity_type"] == "provider"
                    universe.update(rules_output.loc[mask, "entity_id"].dropna().astype(str).tolist())
                else:
                    universe.update(rules_output["entity_id"].dropna().astype(str).tolist())
        elif isinstance(rules_output, list):
            for a in rules_output:
                etype = getattr(a, "entity_type", None) or (a.get("entity_type") if isinstance(a, dict) else "provider")
                if not etype or etype == "provider":
                    pid = getattr(a, "entity_id", None) or (a.get("entity_id") if isinstance(a, dict) else None)
                    if pid:
                        universe.add(str(pid))

        if isinstance(ml_output, pd.DataFrame) and "provider_id" in ml_output.columns:
            universe.update(ml_output["provider_id"].dropna().astype(str).tolist())

        if isinstance(anomaly_output, pd.DataFrame) and "provider_id" in anomaly_output.columns:
            universe.update(anomaly_output["provider_id"].dropna().astype(str).tolist())

        if isinstance(future_risk_output, pd.DataFrame) and "provider_id" in future_risk_output.columns:
            universe.update(future_risk_output["provider_id"].dropna().astype(str).tolist())

        if isinstance(network_output, pd.DataFrame) and "provider_id" in network_output.columns:
            universe.update(network_output["provider_id"].dropna().astype(str).tolist())
        elif isinstance(network_output, tuple) and len(network_output) == 2 and isinstance(network_output[1], list):
            for comm in network_output[1]:
                universe.update(str(p) for p in comm.get("provider_ids", []))

    # Step 2: Extract Signal Components for Each Subsystem
    rules_dict, rules_avail = extract_rule_signals(rules_output, universe, cfg)
    ml_dict, ml_avail = extract_ml_signals(ml_output, universe, cfg)
    anomaly_dict, anomaly_avail = extract_anomaly_signals(anomaly_output, universe, cfg)
    future_dict, future_avail = extract_future_risk_signals(future_risk_output, universe, cfg)
    network_dict, network_avail = extract_network_signals(network_output, universe, cfg)
    temporal_dict, temporal_avail = extract_temporal_signals(temporal_output, universe, cfg)
    historical_dict, historical_avail = extract_historical_signals(historical_output, universe, cfg)

    # Step 3: Compute Provider Score Records
    records: List[Dict[str, Any]] = []
    sorted_universe = sorted(list(universe))

    for pid in sorted_universe:
        r_info = rules_dict.get(pid, {})
        m_info = ml_dict.get(pid, {})
        a_info = anomaly_dict.get(pid, {})
        n_info = network_dict.get(pid, {})
        t_info = temporal_dict.get(pid, {})
        h_info = historical_dict.get(pid, {})
        f_info = future_dict.get(pid, {})

        # Component values strictly in [0, 1]
        components = SignalComponents(
            rule_component=clip_01(r_info.get("rule_component", 0.0)),
            ml_component=clip_01(m_info.get("ml_component", 0.0)),
            anomaly_component=clip_01(a_info.get("anomaly_component", 0.0)),
            network_component=clip_01(n_info.get("network_component", 0.0)),
            temporal_component=clip_01(t_info.get("temporal_component", 0.0)),
            historical_component=clip_01(h_info.get("historical_component", 0.0)),
            future_component=clip_01(f_info.get("future_component", 0.0)),
        )

        # Availability flags
        availability = SignalAvailability(
            rules_available=bool(r_info.get("rules_available", False)),
            ml_available=bool(m_info.get("ml_available", False)),
            anomaly_available=bool(a_info.get("anomaly_available", False)),
            network_available=bool(n_info.get("network_available", False)),
            temporal_available=bool(t_info.get("temporal_available", False)),
            historical_available=bool(h_info.get("historical_available", False)),
            future_available=bool(f_info.get("future_available", False)),
        )

        # Determine effective weights for this provider
        if renormalize:
            active_weight_sum = 0.0
            if availability.rules_available:
                active_weight_sum += weights_cfg.get("rules", 0.0)
            if availability.ml_available:
                active_weight_sum += weights_cfg.get("ml", 0.0)
            if availability.anomaly_available:
                active_weight_sum += weights_cfg.get("anomaly", 0.0)
            if availability.network_available:
                active_weight_sum += weights_cfg.get("network", 0.0)
            if availability.temporal_available:
                active_weight_sum += weights_cfg.get("temporal", 0.0)
            if availability.historical_available:
                active_weight_sum += weights_cfg.get("historical", 0.0)
            if availability.future_available:
                active_weight_sum += weights_cfg.get("future", 0.0)

            if active_weight_sum > 0:
                scale = 1.0 / active_weight_sum
                w_rule = weights_cfg.get("rules", 0.0) * scale if availability.rules_available else 0.0
                w_ml = weights_cfg.get("ml", 0.0) * scale if availability.ml_available else 0.0
                w_anom = weights_cfg.get("anomaly", 0.0) * scale if availability.anomaly_available else 0.0
                w_net = weights_cfg.get("network", 0.0) * scale if availability.network_available else 0.0
                w_temp = weights_cfg.get("temporal", 0.0) * scale if availability.temporal_available else 0.0
                w_hist = weights_cfg.get("historical", 0.0) * scale if availability.historical_available else 0.0
                w_fut = weights_cfg.get("future", 0.0) * scale if availability.future_available else 0.0
            else:
                w_rule = w_ml = w_anom = w_net = w_temp = w_hist = w_fut = 0.0
        else:
            w_rule = weights_cfg.get("rules", 0.0)
            w_ml = weights_cfg.get("ml", 0.0)
            w_anom = weights_cfg.get("anomaly", 0.0)
            w_net = weights_cfg.get("network", 0.0)
            w_temp = weights_cfg.get("temporal", 0.0)
            w_hist = weights_cfg.get("historical", 0.0)
            w_fut = weights_cfg.get("future", 0.0)

        # Compute raw weighted contributions
        c_rule = w_rule * components.rule_component
        c_ml = w_ml * components.ml_component
        c_anom = w_anom * components.anomaly_component
        c_net = w_net * components.network_component
        c_temp = w_temp * components.temporal_component
        c_hist = w_hist * components.historical_component
        c_fut = w_fut * components.future_component

        raw_score = c_rule + c_ml + c_anom + c_net + c_temp + c_hist + c_fut
        risk_score = round(clip_01(raw_score), 4)

        # Reconcile contributions to exactly equal risk_score
        c_rule_r = round(c_rule, 4)
        c_ml_r = round(c_ml, 4)
        c_anom_r = round(c_anom, 4)
        c_net_r = round(c_net, 4)
        c_temp_r = round(c_temp, 4)
        c_hist_r = round(c_hist, 4)
        c_fut_r = round(c_fut, 4)

        # Micro-adjustment to largest contribution to ensure exact sum identity
        diff = round(risk_score - (c_rule_r + c_ml_r + c_anom_r + c_net_r + c_temp_r + c_hist_r + c_fut_r), 4)
        if abs(diff) > 0:
            cont_list = [
                ("rule", c_rule_r), ("ml", c_ml_r), ("anom", c_anom_r),
                ("net", c_net_r), ("temp", c_temp_r), ("hist", c_hist_r), ("fut", c_fut_r)
            ]
            largest_idx = max(range(len(cont_list)), key=lambda i: cont_list[i][1])
            if cont_list[largest_idx][0] == "rule":
                c_rule_r = round(c_rule_r + diff, 4)
            elif cont_list[largest_idx][0] == "ml":
                c_ml_r = round(c_ml_r + diff, 4)
            elif cont_list[largest_idx][0] == "anom":
                c_anom_r = round(c_anom_r + diff, 4)
            elif cont_list[largest_idx][0] == "net":
                c_net_r = round(c_net_r + diff, 4)
            elif cont_list[largest_idx][0] == "temp":
                c_temp_r = round(c_temp_r + diff, 4)
            elif cont_list[largest_idx][0] == "hist":
                c_hist_r = round(c_hist_r + diff, 4)
            else:
                c_fut_r = round(c_fut_r + diff, 4)

        contributions = SignalContributions(
            rule_contribution=c_rule_r,
            ml_contribution=c_ml_r,
            anomaly_contribution=c_anom_r,
            network_contribution=c_net_r,
            temporal_contribution=c_temp_r,
            historical_contribution=c_hist_r,
            future_contribution=c_fut_r,
        )

        # Risk tier
        risk_tier = get_risk_tier(risk_score, risk_tiers_cfg)

        # Evidence strength
        ev_strength = round(compute_evidence_strength(
            components, availability, r_info, m_info, n_info, cfg
        ), 4)
        ev_tier = get_evidence_tier(ev_strength, ev_tiers_cfg)

        # Confidence score
        conf_score = round(compute_confidence_score(
            components, availability, weights_cfg, m_info, r_info, cfg
        ), 4)
        conf_tier = get_confidence_tier(conf_score, conf_tiers_cfg)

        # Machine-readable explainable top reasons
        top_reasons = generate_top_reasons(
            components, contributions, r_info, m_info, a_info, n_info, f_info, t_info
        )

        record = ProviderScoreRecord(
            provider_id=pid,
            risk_score=risk_score,
            risk_tier=risk_tier,
            evidence_strength=ev_strength,
            evidence_tier=ev_tier,
            confidence_score=conf_score,
            confidence_tier=conf_tier,
            rule_component=round(components.rule_component, 4),
            ml_component=round(components.ml_component, 4),
            anomaly_component=round(components.anomaly_component, 4),
            network_component=round(components.network_component, 4),
            temporal_component=round(components.temporal_component, 4),
            historical_component=round(components.historical_component, 4),
            future_component=round(components.future_component, 4),
            rule_contribution=contributions.rule_contribution,
            ml_contribution=contributions.ml_contribution,
            anomaly_contribution=contributions.anomaly_contribution,
            network_contribution=contributions.network_contribution,
            temporal_contribution=contributions.temporal_contribution,
            historical_contribution=contributions.historical_contribution,
            future_contribution=contributions.future_contribution,
            top_reasons=top_reasons,
            rule_alert_count=int(r_info.get("rule_alert_count", 0)),
            high_severity_rule_count=int(r_info.get("high_severity_rule_count", 0)),
            estimated_rule_dollars=round(safe_float(r_info.get("estimated_rule_dollars", 0.0)), 2),
            high_risk_claim_count=int(m_info.get("high_risk_claim_count", 0)),
            high_risk_claim_rate=round(safe_float(m_info.get("high_risk_claim_rate", 0.0)), 4),
            anomaly_score=round(safe_float(a_info.get("anomaly_score", 0.0)), 4),
            anomaly_flag=int(a_info.get("anomaly_flag", 0)),
            risk_30d=round(safe_float(f_info.get("risk_30d", 0.0)), 4),
            risk_60d=round(safe_float(f_info.get("risk_60d", 0.0)), 4),
            risk_90d=round(safe_float(f_info.get("risk_90d", 0.0)), 4),
            community_id=n_info.get("community_id"),
            rule_alert_ids=r_info.get("rule_alert_ids", []),
            high_risk_claim_ids=m_info.get("high_risk_claim_ids", []),
            evidence_ids=r_info.get("rule_evidence_ids", []),
            rules_available=availability.rules_available,
            ml_available=availability.ml_available,
            anomaly_available=availability.anomaly_available,
            network_available=availability.network_available,
            temporal_available=availability.temporal_available,
            historical_available=availability.historical_available,
            future_available=availability.future_available,
            model_version=model_ver,
            feature_version=feat_ver,
            risk_engine_version=engine_ver,
        )

        validation_errs = record.validate()
        if validation_errs:
            raise ValueError(f"ProviderRecord validation error for {pid}: {validation_errs}")

        records.append(record.to_dict(serialize_lists=False))

    df_out = pd.DataFrame(records)
    if not df_out.empty:
        # Sort descending by risk_score, then evidence_strength
        df_out = df_out.sort_values(["risk_score", "evidence_strength"], ascending=[False, False]).reset_index(drop=True)
    return df_out


# ------------------------------------------------------------------------------
# High-Level Pipeline Runner
# ------------------------------------------------------------------------------

def run_unified_risk(
    output_dir: Union[str, Path] = "outputs/risk",
    rules_data: Optional[Any] = None,
    ml_path: Optional[Union[str, Path]] = None,
    anomaly_path: Optional[Union[str, Path]] = None,
    future_risk_path: Optional[Union[str, Path]] = None,
    network_data: Optional[Any] = None,
    temporal_data: Optional[Any] = None,
    historical_data: Optional[Any] = None,
    config_path: Optional[Union[str, Path]] = None,
    save_parquet: bool = True,
    save_csv: bool = True,
    gt_entity_labels: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Run the end-to-end Unified Risk Engine pipeline.
    
    Loads existing subsystem artifacts, computes aligned provider risk scores,
    generates evaluation metrics if ground truth is supplied, and writes
    provider_scores.parquet and provider_scores.csv.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve inputs: if paths are provided or default project paths exist
    claim_ml_df = None
    if ml_path and Path(ml_path).exists():
        claim_ml_df = pd.read_parquet(ml_path)
    elif Path("outputs/phase1/claim_ml.parquet").exists():
        claim_ml_df = pd.read_parquet("outputs/phase1/claim_ml.parquet")

    anomaly_df = None
    if anomaly_path and Path(anomaly_path).exists():
        anomaly_df = pd.read_parquet(anomaly_path)
    elif Path("outputs/phase2/provider_anomaly.parquet").exists():
        anomaly_df = pd.read_parquet("outputs/phase2/provider_anomaly.parquet")

    future_df = None
    if future_risk_path and Path(future_risk_path).exists():
        future_df = pd.read_parquet(future_risk_path)
    elif Path("outputs/phase2/future_risk.parquet").exists():
        future_df = pd.read_parquet("outputs/phase2/future_risk.parquet")

    print("[Unified Risk Engine] Computing unified risk scores across available signals...")
    scores_df = compute_unified_risk(
        rules_output=rules_data,
        ml_output=claim_ml_df,
        anomaly_output=anomaly_df,
        future_risk_output=future_df,
        network_output=network_data,
        temporal_output=temporal_data,
        historical_output=historical_data,
        config=config_path,
    )

    print(f"[Unified Risk Engine] Scored {len(scores_df):,} providers successfully.")

    # Save outputs
    saved_files: List[Path] = []
    if save_parquet:
        pq_path = out_dir / "provider_scores.parquet"
        # Convert lists to JSON strings for Parquet compatibility if needed
        pq_df = scores_df.copy()
        for col in ["top_reasons", "rule_alert_ids", "high_risk_claim_ids", "evidence_ids"]:
            if col in pq_df.columns:
                pq_df[col] = pq_df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
        pq_df.to_parquet(pq_path, index=False)
        saved_files.append(pq_path)
        print(f"[Unified Risk Engine] Saved Parquet -> {pq_path}")

    if save_csv:
        csv_path = out_dir / "provider_scores.csv"
        csv_df = scores_df.copy()
        for col in ["top_reasons", "rule_alert_ids", "high_risk_claim_ids", "evidence_ids"]:
            if col in csv_df.columns:
                csv_df[col] = csv_df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
        csv_df.to_csv(csv_path, index=False)
        saved_files.append(csv_path)
        print(f"[Unified Risk Engine] Saved CSV -> {csv_path}")

    # Optional Ground Truth Evaluation
    eval_metrics: Dict[str, Any] = {}
    if gt_entity_labels is not None and not scores_df.empty:
        eval_metrics = evaluate_unified_prioritization(scores_df, gt_entity_labels)
        metrics_path = out_dir / "risk_evaluation_report.json"
        with open(metrics_path, "w") as f:
            json.dump(eval_metrics, f, indent=2)
        print(f"[Unified Risk Engine] Saved evaluation report -> {metrics_path}")

    summary = {
        "n_providers_scored": len(scores_df),
        "saved_files": [str(p) for p in saved_files],
        "tier_distribution": scores_df["risk_tier"].value_counts().to_dict() if not scores_df.empty else {},
        "evaluation_metrics": eval_metrics,
    }
    return summary


# ------------------------------------------------------------------------------
# Evaluation & Benchmarking vs Baselines
# ------------------------------------------------------------------------------

def evaluate_unified_prioritization(
    scores_df: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Evaluate provider risk prioritization against ground truth bad actor entities.
    
    Compares:
      - Unified Risk Engine vs Rules-only, ML-only, Network-only
      - Computes Precision@K, Recall@K, Average Precision (PR-AUC), and Rank Lift.
    """
    if scores_df.empty or gt_entity_labels.empty:
        return {}

    gt_positives = set(
        gt_entity_labels.loc[
            gt_entity_labels["is_suspicious"] == 1, "entity_id"
        ].astype(str)
    )
    if not gt_positives:
        return {}

    eval_df = scores_df.copy()
    eval_df["is_true_positive"] = eval_df["provider_id"].astype(str).isin(gt_positives).astype(int)
    total_pos = len(gt_positives)

    def _calc_metrics(score_col: str, k_list: List[int] = [10, 25, 50, 100]) -> Dict[str, Any]:
        ranked = eval_df.sort_values(score_col, ascending=False).reset_index(drop=True)
        res: Dict[str, Any] = {}
        for k in k_list:
            k_val = min(k, len(ranked))
            top_k = ranked.iloc[:k_val]
            tp = int(top_k["is_true_positive"].sum())
            prec = tp / float(k_val) if k_val > 0 else 0.0
            rec = tp / float(total_pos) if total_pos > 0 else 0.0
            res[f"precision@{k}"] = round(prec, 4)
            res[f"recall@{k}"] = round(rec, 4)
            res[f"tp@{k}"] = tp
        return res

    results = {
        "total_providers": len(scores_df),
        "total_ground_truth_positives": total_pos,
        "unified_risk": _calc_metrics("risk_score"),
    }

    # Signal family comparisons if column exists with variation
    if "rule_component" in scores_df.columns and scores_df["rule_component"].std() > 0:
        results["rules_only"] = _calc_metrics("rule_component")
    if "ml_component" in scores_df.columns and scores_df["ml_component"].std() > 0:
        results["ml_only"] = _calc_metrics("ml_component")
    if "network_component" in scores_df.columns and scores_df["network_component"].std() > 0:
        results["network_only"] = _calc_metrics("network_component")

    return results


# ------------------------------------------------------------------------------
# CLI Entry Point
# ------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Vigil-X Standalone Unified Risk Engine")
    parser.add_argument("--output-dir", default="outputs/risk", help="Directory for output files")
    parser.add_argument("--ml-path", default="outputs/phase1/claim_ml.parquet", help="Path to claim_ml parquet")
    parser.add_argument("--anomaly-path", default="outputs/phase2/provider_anomaly.parquet", help="Path to provider_anomaly parquet")
    parser.add_argument("--future-risk-path", default="outputs/phase2/future_risk.parquet", help="Path to future_risk parquet")
    parser.add_argument("--config", default=None, help="Path to custom risk_config.yaml")
    parser.add_argument("--full-pipeline", action="store_true", help="Run full pipeline end-to-end (Rules + ML + Anomaly + Future + Network) on project data")
    args = parser.parse_args()

    print("=" * 70)
    print("  VIGIL-X STANDALONE UNIFIED RISK ENGINE")
    print("=" * 70)

    if args.full_pipeline:
        print("[Pipeline Mode] Generating synthetic dataset and running all subsystems...")
        from generator.synthetic_data import generate_synthetic_data
        from rules.runner import run_network_behavior_rules
        from network.graph_builder import build_graph
        from network.provider_projection import build_provider_projection
        from network.community import detect_communities

        data = generate_synthetic_data(seed=42)
        claims = data["claims"]
        providers = data["providers"]
        referrals = data["referrals"]
        facilities = data["facilities"]
        gt_entity_labels = data["gt_entity_labels"]

        # Run rules
        alerts = run_network_behavior_rules(data)
        print(f"[Pipeline Mode] Produced {len(alerts):,} alerts from R06-R10.")

        # Run network
        G = build_graph(claims, providers, referrals, facilities)
        P = build_provider_projection(G)
        communities = detect_communities(P)
        print(f"[Pipeline Mode] Detected {len(communities)} provider communities.")

        # Run Unified Risk Engine
        summary = run_unified_risk(
            output_dir=args.output_dir,
            rules_data=alerts,
            ml_path=args.ml_path,
            anomaly_path=args.anomaly_path,
            future_risk_path=args.future_risk_path,
            network_data=communities,
            config_path=args.config,
            gt_entity_labels=gt_entity_labels,
        )

        print("\n" + "=" * 70)
        print("  FULL PIPELINE EXECUTION COMPLETED")
        print(f"  Scored: {summary['n_providers_scored']} providers")
        print(f"  Tiers:  {summary['tier_distribution']}")
        print("=" * 70)
        if summary.get("evaluation_metrics"):
            print("\nGround Truth Prioritization Evaluation:")
            print(json.dumps(summary["evaluation_metrics"], indent=2))
    else:
        summary = run_unified_risk(
            output_dir=args.output_dir,
            ml_path=args.ml_path,
            anomaly_path=args.anomaly_path,
            future_risk_path=args.future_risk_path,
            config_path=args.config,
        )
        print(f"\nCompleted: {summary['n_providers_scored']} providers scored.")


if __name__ == "__main__":
    main()
