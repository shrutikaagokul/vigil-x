"""
Priority Engine for the Vigil-X SIU Priority Queue subsystem.

Computes deterministic, explainable, capacity-aware priority scores for
investigation cases using existing multi-signal intelligence, robust signal
normalization, missing-signal weight renormalization, and defensive explanations.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
import yaml

from cases.contracts import InvestigationCase
from siu.contracts import (
    PROHIBITED_TERMS,
    SIUPriorityTier,
)

DEFAULT_CONFIG_PATH = Path(__file__).parent / "queue_config.yaml"


# ------------------------------------------------------------------------------
# Configuration Loader
# ------------------------------------------------------------------------------

def load_queue_config(config_input: Optional[Union[Dict[str, Any], Path, str]] = None) -> Dict[str, Any]:
    """Load and validate SIU Priority Queue configuration."""
    if config_input is None:
        cfg_path = DEFAULT_CONFIG_PATH
        if not cfg_path.exists():
            raise FileNotFoundError(f"SIU config not found: {cfg_path}")
        with open(cfg_path, "r") as f:
            cfg = yaml.safe_load(f)
    elif isinstance(config_input, (str, Path)):
        cfg_path = Path(config_input)
        if not cfg_path.exists():
            raise FileNotFoundError(f"SIU config not found: {cfg_path}")
        with open(cfg_path, "r") as f:
            cfg = yaml.safe_load(f)
    elif isinstance(config_input, dict):
        cfg = config_input.copy()
    else:
        raise TypeError(f"Unsupported config type: {type(config_input)}")

    # Validate weights sum to 1.0 within floating point tolerance
    siu_cfg = cfg.get("siu", {})
    weights = siu_cfg.get("weights", {})
    total_w = sum(weights.values())
    if abs(total_w - 1.0) > 1e-4:
        raise ValueError(f"SIU weights must sum to 1.0, got {total_w:.4f} ({weights})")

    return cfg


# ------------------------------------------------------------------------------
# Safe Extractors & Helpers
# ------------------------------------------------------------------------------

def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _clip_01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _get_case_val(case: Union[InvestigationCase, Dict[str, Any]], field_name: str, default: Any = None) -> Any:
    if isinstance(case, dict):
        return case.get(field_name, default)
    return getattr(case, field_name, default)


# ------------------------------------------------------------------------------
# Signal Derivation Functions
# ------------------------------------------------------------------------------

def derive_risk_signal(case: Union[InvestigationCase, Dict[str, Any]]) -> Tuple[float, bool]:
    """Derive normalized risk score signal [0, 1]."""
    val = _get_case_val(case, "risk_score", None)
    if val is None:
        return 0.0, False
    return _clip_01(_safe_float(val)), True


def derive_evidence_signal(case: Union[InvestigationCase, Dict[str, Any]]) -> Tuple[float, bool]:
    """Derive normalized evidence strength signal [0, 1]."""
    val = _get_case_val(case, "evidence_strength", None)
    if val is None:
        return 0.0, False
    return _clip_01(_safe_float(val)), True


def derive_exposure_signal(
    exposure: float,
    log_min: float = 0.0,
    log_max: float = 0.0,
) -> float:
    """
    Derive normalized financial exposure signal [0, 1].
    
    Uses log1p transformation to prevent outlier exposures from dominating the queue,
    followed by min-max scaling across dataset bounds.
    """
    exp_safe = max(0.0, _safe_float(exposure))
    v = math.log1p(exp_safe)

    if log_max > log_min:
        norm = (v - log_min) / (log_max - log_min)
        return _clip_01(norm)

    # Fallback for single-case or uniform dataset: soft reference ceiling ($100,000)
    ref_ceiling = math.log1p(100000.0)
    return _clip_01(v / ref_ceiling)


def derive_network_signal(case: Union[InvestigationCase, Dict[str, Any]]) -> Tuple[float, bool]:
    """
    Derive deterministic network connectivity signal [0, 1].
    
    Factors:
      - community_id presence: +0.30
      - relationship count: up to +0.40 (0.10 per connected peer, capped at 4)
      - average relationship strength: up to +0.30
    """
    comm_id = _get_case_val(case, "community_id", None)
    rels = _get_case_val(case, "network_relationships", [])
    if isinstance(rels, str):
        try:
            rels = json.loads(rels)
        except Exception:
            rels = []

    has_comm = comm_id is not None and str(comm_id).strip() != "" and str(comm_id) != "None"
    has_rels = isinstance(rels, list) and len(rels) > 0

    if not has_comm and not has_rels:
        return 0.0, False

    signal = 0.0
    if has_comm:
        signal += 0.30

    if has_rels:
        n_rels = len(rels)
        signal += min(0.40, 0.10 * n_rels)

        strengths = []
        for r in rels:
            if isinstance(r, dict):
                strengths.append(_safe_float(r.get("strength", 0.5)))
        avg_str = sum(strengths) / len(strengths) if strengths else 0.5
        signal += 0.30 * _clip_01(avg_str)

    return _clip_01(signal), True


def derive_anomaly_signal(case: Union[InvestigationCase, Dict[str, Any]]) -> Tuple[float, bool]:
    """
    Derive provider behavioral anomaly signal [0, 1].
    
    Consumes anomaly_score and anomaly_flag from behavioral analysis.
    """
    score_raw = _get_case_val(case, "anomaly_score", None)
    flag_raw = _get_case_val(case, "anomaly_flag", None)

    if score_raw is None and flag_raw is None:
        return 0.0, False

    score = _safe_float(score_raw, 0.0)
    flag = _safe_int(flag_raw, 0)

    # Normalize safely to [0, 1] without reinterpreting as probability
    if flag == 1:
        # High percentile anomaly detected
        norm = 0.60 + 0.40 * _clip_01(score / 0.35 if score > 0 else 0.0)
    else:
        # Non-flagged provider: scale from low baseline
        if score > 0:
            norm = min(0.50, 0.50 * (score / 0.35))
        else:
            # Negative isolation forest score (typical inliers)
            norm = max(0.0, min(0.20, (score + 0.10) / 0.20 * 0.20))

    return _clip_01(norm), True


def derive_future_risk_signal(case: Union[InvestigationCase, Dict[str, Any]]) -> Tuple[float, bool]:
    """
    Derive future risk trajectory signal [0, 1].
    
    Takes the maximum across available future risk horizons (30d, 60d, 90d).
    """
    r30 = _get_case_val(case, "risk_30d", None)
    r60 = _get_case_val(case, "risk_60d", None)
    r90 = _get_case_val(case, "risk_90d", None)

    available = []
    for h in [r30, r60, r90]:
        if h is not None:
            f = _safe_float(h)
            if not (math.isnan(f) or math.isinf(f)):
                available.append(f)

    if not available:
        return 0.0, False

    # Maximum future horizon risk bounded to [0, 1]
    return _clip_01(max(available)), True


def derive_behavioral_signal(case: Union[InvestigationCase, Dict[str, Any]]) -> Tuple[float, bool]:
    """
    Derive conservative behavioral claim signal [0, 1].
    
    Combines high-risk claim concentration, rule alert density,
    severity ratio, and rule diversity.
    """
    claim_count = _safe_int(_get_case_val(case, "claim_count", 0))
    hr_claims = _safe_int(_get_case_val(case, "high_risk_claim_count", 0))
    alert_count = _safe_int(_get_case_val(case, "rule_alert_count", 0))
    hi_sev = _safe_int(_get_case_val(case, "high_severity_rule_count", 0))
    distinct_rules = _safe_int(_get_case_val(case, "distinct_rule_count", 0))

    if claim_count == 0 and alert_count == 0:
        return 0.0, False

    # 1. High risk claim ratio
    hr_ratio = min(1.0, hr_claims / max(1, claim_count)) if claim_count > 0 else 0.0
    # 2. Alert volume density (normalized against 10 alerts benchmark)
    alert_density = min(1.0, alert_count / 10.0)
    # 3. High severity rule proportion
    sev_ratio = min(1.0, hi_sev / max(1, alert_count)) if alert_count > 0 else 0.0
    # 4. Distinct rule diversity (normalized against 5 rules benchmark)
    rule_diversity = min(1.0, distinct_rules / 5.0)

    score = (
        0.35 * hr_ratio +
        0.25 * alert_density +
        0.20 * sev_ratio +
        0.20 * rule_diversity
    )
    return _clip_01(score), True


# ------------------------------------------------------------------------------
# Priority Score & Explanation Synthesizer
# ------------------------------------------------------------------------------

def compute_case_signals(
    case: Union[InvestigationCase, Dict[str, Any]],
    exposure_bounds: Optional[Tuple[float, float]] = None,
) -> Tuple[Dict[str, float], Set[str]]:
    """
    Compute all normalized signal components and set of active signals.
    """
    signals: Dict[str, float] = {}
    active: Set[str] = set()

    # 1. Risk
    r_val, r_act = derive_risk_signal(case)
    signals["risk_score"] = r_val
    if r_act:
        active.add("risk_score")

    # 2. Evidence
    e_val, e_act = derive_evidence_signal(case)
    signals["evidence_strength"] = e_val
    if e_act:
        active.add("evidence_strength")

    # 3. Exposure
    raw_exp = _get_case_val(case, "estimated_exposure", None)
    if raw_exp is not None:
        log_min = exposure_bounds[0] if exposure_bounds else 0.0
        log_max = exposure_bounds[1] if exposure_bounds else 0.0
        signals["estimated_exposure"] = derive_exposure_signal(raw_exp, log_min, log_max)
        active.add("estimated_exposure")
    else:
        signals["estimated_exposure"] = 0.0

    # 4. Network
    n_val, n_act = derive_network_signal(case)
    signals["network_signal"] = n_val
    if n_act:
        active.add("network_signal")

    # 5. Anomaly
    a_val, a_act = derive_anomaly_signal(case)
    signals["anomaly_signal"] = a_val
    if a_act:
        active.add("anomaly_signal")

    # 6. Future Risk
    f_val, f_act = derive_future_risk_signal(case)
    signals["future_risk_signal"] = f_val
    if f_act:
        active.add("future_risk_signal")

    # 7. Behavioral
    b_val, b_act = derive_behavioral_signal(case)
    signals["behavioral_signal"] = b_val
    if b_act:
        active.add("behavioral_signal")

    return signals, active


def compute_priority_score(
    case: Union[InvestigationCase, Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
    exposure_bounds: Optional[Tuple[float, float]] = None,
) -> float:
    """
    Compute deterministic priority score for an investigation case.
    
    Renormalizes nominal weights across available signals.
    """
    cfg = load_queue_config(config)
    weights = cfg.get("siu", {}).get("weights", {})

    signals, active = compute_case_signals(case, exposure_bounds)

    active_weight_sum = sum(weights.get(k, 0.0) for k in active)
    if active_weight_sum <= 0:
        return 0.0

    weighted_score = sum(weights.get(k, 0.0) * signals.get(k, 0.0) for k in active)
    priority_score = weighted_score / active_weight_sum
    return _clip_01(priority_score)


def determine_priority_tier(priority_score: float, thresholds: Dict[str, float]) -> str:
    """Map priority score to operational SIUPriorityTier."""
    crit_th = float(thresholds.get("critical", 0.80))
    high_th = float(thresholds.get("high", 0.60))
    med_th = float(thresholds.get("medium", 0.35))

    if priority_score >= crit_th:
        return SIUPriorityTier.CRITICAL.value
    elif priority_score >= high_th:
        return SIUPriorityTier.HIGH.value
    elif priority_score >= med_th:
        return SIUPriorityTier.MEDIUM.value
    else:
        return SIUPriorityTier.LOW.value


def generate_priority_reasons(
    case: Union[InvestigationCase, Dict[str, Any]],
    signals: Dict[str, float],
    max_reasons: int = 5,
) -> List[str]:
    """
    Generate deterministic, evidence-backed priority reasons.
    
    Adheres strictly to defensive SIU language with zero fraud-confirmation terms.
    """
    candidates: List[Tuple[float, str]] = []

    risk_score = _safe_float(_get_case_val(case, "risk_score", 0.0))
    ev_strength = _safe_float(_get_case_val(case, "evidence_strength", 0.0))
    exposure = _safe_float(_get_case_val(case, "estimated_exposure", 0.0))
    comm_id = _get_case_val(case, "community_id", None)
    anom_flag = _safe_int(_get_case_val(case, "anomaly_flag", 0))
    hr_claims = _safe_int(_get_case_val(case, "high_risk_claim_count", 0))
    distinct_rules = _safe_int(_get_case_val(case, "distinct_rule_count", 0))
    alert_count = _safe_int(_get_case_val(case, "rule_alert_count", 0))
    fut_signal = signals.get("future_risk_signal", 0.0)

    # 1. Unified Risk
    if risk_score >= 0.40:
        candidates.append((0.95, f"High unified risk prioritization score ({risk_score:.3f})"))
    elif risk_score >= 0.25:
        candidates.append((0.75, f"Elevated unified risk prioritization score ({risk_score:.3f})"))

    # 2. Supporting Evidence
    if ev_strength >= 0.70:
        candidates.append((0.90, f"High supporting evidence strength ({ev_strength:.3f})"))
    elif ev_strength >= 0.50:
        candidates.append((0.70, f"Substantial corroborating evidence strength ({ev_strength:.3f})"))

    # 3. Financial Exposure
    if exposure >= 50000.0:
        candidates.append((0.85, f"High estimated financial exposure (${exposure:,.2f})"))
    elif exposure >= 5000.0:
        candidates.append((0.65, f"Identified financial exposure (${exposure:,.2f})"))

    # 4. Network Community
    if comm_id is not None and str(comm_id).strip() != "" and str(comm_id) != "None":
        candidates.append((0.80, f"Affiliated with network community #{comm_id}"))

    # 5. Behavioral Anomaly
    if anom_flag == 1 or signals.get("anomaly_signal", 0.0) >= 0.60:
        candidates.append((0.75, "Statistical behavioral billing anomaly flagged"))

    # 6. Future Risk
    if fut_signal >= 0.05:
        candidates.append((0.70, f"Elevated future risk trajectory ({fut_signal:.3f})"))

    # 7. Concentrated High-Risk Claims
    if hr_claims >= 20:
        candidates.append((0.82, f"Concentrated high-risk claim transactions ({hr_claims} claims)"))
    elif hr_claims > 0:
        candidates.append((0.60, f"Contains {hr_claims} flagged high-risk claim(s)"))

    # 8. Detection Rules
    if distinct_rules >= 3:
        candidates.append((0.78, f"Triggered multiple independent detection rules ({distinct_rules} rules, {alert_count} alerts)"))
    elif alert_count >= 5:
        candidates.append((0.65, f"Multiple detection rule alerts ({alert_count} alerts)"))

    # Sort candidates by importance weight descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    selected_reasons = [item[1] for item in candidates[:max_reasons]]

    if not selected_reasons:
        selected_reasons.append("Prioritized for investigation based on consolidated risk signals")

    # Safety assertion: check no prohibited terms
    clean_reasons: List[str] = []
    for r in selected_reasons:
        lower_r = r.lower()
        if not any(term in lower_r for term in PROHIBITED_TERMS):
            clean_reasons.append(r)

    return clean_reasons[:max_reasons]


# ------------------------------------------------------------------------------
# CLI Runner Hook
# ------------------------------------------------------------------------------

def main():
    """CLI hook for running SIU Priority Queue."""
    import argparse
    from siu.capacity_optimizer import run_siu_pipeline

    parser = argparse.ArgumentParser(description="Vigil-X SIU Priority Queue")
    parser.add_argument("--cases", default="outputs/cases/cases.parquet", help="Path to cases parquet or csv")
    parser.add_argument("--config", default=None, help="Path to queue_config.yaml")
    parser.add_argument("--capacity", type=int, default=None, help="Daily investigator capacity")
    parser.add_argument("--outdir", default="outputs/siu", help="Output directory")
    args = parser.parse_args()

    run_siu_pipeline(
        cases_input=args.cases,
        config_path=args.config,
        daily_capacity=args.capacity,
        output_dir=args.outdir,
    )


if __name__ == "__main__":
    main()
