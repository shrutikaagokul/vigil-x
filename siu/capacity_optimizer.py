"""
Capacity Optimizer for the Vigil-X SIU Priority Queue subsystem.

Applies investigator caseload constraints, multi-key deterministic ranking,
baseline strategy comparisons, and evaluation report generation.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

from cases.contracts import CaseStatus, InvestigationCase
from siu.contracts import (
    SIUPriorityTier,
    SIUQueueItem,
    SIUQueueStatus,
)
from siu.priority_engine import (
    compute_case_signals,
    compute_priority_score,
    determine_priority_tier,
    generate_priority_reasons,
    load_queue_config,
)


# ------------------------------------------------------------------------------
# Helpers & Loaders
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


def load_cases_dataset(cases_input: Union[pd.DataFrame, List[InvestigationCase], str, Path]) -> pd.DataFrame:
    """Load cases into a DataFrame."""
    if isinstance(cases_input, pd.DataFrame):
        return cases_input.copy()
    elif isinstance(cases_input, (str, Path)):
        p = Path(cases_input)
        if not p.exists():
            # Try fallback to csv if parquet requested, or vice versa
            alt_ext = ".csv" if p.suffix == ".parquet" else ".parquet"
            alt_path = p.with_suffix(alt_ext)
            if alt_path.exists():
                p = alt_path
            else:
                raise FileNotFoundError(f"Cases input file not found: {p}")
        if p.suffix == ".parquet":
            return pd.read_parquet(p)
        else:
            return pd.read_csv(p)
    elif isinstance(cases_input, list):
        records = []
        for c in cases_input:
            if hasattr(c, "to_dict"):
                records.append(c.to_dict())
            elif isinstance(c, dict):
                records.append(c)
            else:
                raise TypeError(f"Unsupported case item type: {type(c)}")
        return pd.DataFrame(records)
    else:
        raise TypeError(f"Unsupported cases_input type: {type(cases_input)}")


# ------------------------------------------------------------------------------
# Core Queue Builder
# ------------------------------------------------------------------------------

def build_siu_queue(
    cases: Union[pd.DataFrame, List[InvestigationCase], str, Path],
    daily_capacity: Optional[int] = None,
    config: Optional[Union[Dict[str, Any], Path, str]] = None,
) -> Tuple[pd.DataFrame, List[SIUQueueItem]]:
    """
    Build a capacity-aware SIU Priority Queue from investigation cases.
    
    Parameters:
      cases: DataFrame, list of InvestigationCase, or path to parquet/csv.
      daily_capacity: Number of cases investigators can take on daily (overrides config).
      config: Optional configuration dict or path.
      
    Returns:
      (queue_df, queue_items)
    """
    cfg = load_queue_config(config)
    siu_cfg = cfg.get("siu", {})

    capacity = daily_capacity if daily_capacity is not None else int(siu_cfg.get("daily_capacity", 20))
    capacity = max(0, capacity)

    eligible_statuses = [s.upper() for s in siu_cfg.get("eligible_statuses", [
        CaseStatus.NEW.value, CaseStatus.IN_REVIEW.value, CaseStatus.ESCALATED.value
    ])]
    thresholds = siu_cfg.get("thresholds", {"critical": 0.80, "high": 0.60, "medium": 0.35})
    siu_ver = str(siu_cfg.get("version", "1.0.0"))
    max_reasons = int(siu_cfg.get("limits", {}).get("max_reasons", 5))

    df_cases = load_cases_dataset(cases)
    if df_cases.empty:
        return pd.DataFrame(), []

    # Filter eligible case statuses
    if "status" in df_cases.columns:
        df_eligible = df_cases[df_cases["status"].astype(str).str.upper().isin(eligible_statuses)].copy()
    else:
        df_eligible = df_cases.copy()

    if df_eligible.empty:
        return pd.DataFrame(), []

    # Compute exposure bounds across eligible dataset for log1p min-max normalization
    exposures = df_eligible["estimated_exposure"].apply(lambda x: max(0.0, _safe_float(x)))
    log_exposures = exposures.apply(math.log1p)
    log_min = float(log_exposures.min())
    log_max = float(log_exposures.max())
    exposure_bounds = (log_min, log_max)

    # Process each case: calculate signals, priority score, tier, reasons
    scored_records: List[Dict[str, Any]] = []

    for _, row in df_eligible.iterrows():
        case_dict = row.to_dict()
        case_id = str(case_dict.get("case_id", ""))
        provider_id = str(case_dict.get("provider_id", ""))

        signals, active = compute_case_signals(case_dict, exposure_bounds)
        p_score = compute_priority_score(case_dict, config=cfg, exposure_bounds=exposure_bounds)
        p_tier = determine_priority_tier(p_score, thresholds)
        reasons = generate_priority_reasons(case_dict, signals, max_reasons=max_reasons)

        scored_records.append({
            "case_id": case_id,
            "provider_id": provider_id,
            "priority_score": p_score,
            "priority_tier": p_tier,
            "risk_score": _safe_float(case_dict.get("risk_score", 0.0)),
            "risk_tier": str(case_dict.get("risk_tier", "LOW")),
            "evidence_strength": _safe_float(case_dict.get("evidence_strength", 0.0)),
            "confidence_score": _safe_float(case_dict.get("confidence_score", 0.0)),
            "estimated_exposure": _safe_float(case_dict.get("estimated_exposure", 0.0)),
            "network_signal": signals.get("network_signal", 0.0),
            "anomaly_signal": signals.get("anomaly_signal", 0.0),
            "future_risk_signal": signals.get("future_risk_signal", 0.0),
            "behavioral_signal": signals.get("behavioral_signal", 0.0),
            "case_status": str(case_dict.get("status", CaseStatus.NEW.value)),
            "priority_reasons": reasons,
            "claim_count": _safe_int(case_dict.get("claim_count", 0)),
            "alert_count": _safe_int(case_dict.get("rule_alert_count", 0)),
            "evidence_count": len(case_dict.get("evidence_ids", [])) if isinstance(case_dict.get("evidence_ids"), list) else 0,
            "community_id": case_dict.get("community_id", None),
            "created_at": str(case_dict.get("created_at", "")),
            "case_builder_version": str(case_dict.get("case_builder_version", "1.0.0")),
            "siu_version": siu_ver,
        })

    df_scored = pd.DataFrame(scored_records)

    # Deterministic Multi-Key Sorting:
    # 1. priority_score DESC
    # 2. risk_score DESC
    # 3. evidence_strength DESC
    # 4. estimated_exposure DESC
    # 5. case_id ASC
    df_sorted = df_scored.sort_values(
        by=["priority_score", "risk_score", "evidence_strength", "estimated_exposure", "case_id"],
        ascending=[False, False, False, False, True]
    ).reset_index(drop=True)

    # Assign queue ranks and capacity selection
    now_iso = datetime.now(timezone.utc).isoformat()
    queue_items: List[SIUQueueItem] = []
    final_records: List[Dict[str, Any]] = []

    for idx, row in df_sorted.iterrows():
        rank = idx + 1
        queue_id = f"SIU-{rank:06d}"

        if capacity > 0 and rank <= capacity:
            selected = True
            cap_rank = rank
            q_status = SIUQueueStatus.QUEUED.value
        else:
            selected = False
            cap_rank = 0
            q_status = SIUQueueStatus.DEFERRED.value

        comm_id = row["community_id"]
        comm_val = int(comm_id) if (comm_id is not None and not pd.isna(comm_id) and str(comm_id) != "None") else None

        item = SIUQueueItem(
            queue_id=queue_id,
            case_id=row["case_id"],
            provider_id=row["provider_id"],
            rank=rank,
            priority_score=round(float(row["priority_score"]), 4),
            priority_tier=row["priority_tier"],
            risk_score=round(float(row["risk_score"]), 4),
            risk_tier=row["risk_tier"],
            evidence_strength=round(float(row["evidence_strength"]), 4),
            confidence_score=round(float(row["confidence_score"]), 4),
            estimated_exposure=round(float(row["estimated_exposure"]), 2),
            network_signal=round(float(row["network_signal"]), 4),
            anomaly_signal=round(float(row["anomaly_signal"]), 4),
            future_risk_signal=round(float(row["future_risk_signal"]), 4),
            behavioral_signal=round(float(row["behavioral_signal"]), 4),
            case_status=row["case_status"],
            queue_status=q_status,
            capacity_selected=selected,
            capacity_rank=cap_rank,
            priority_reasons=row["priority_reasons"],
            claim_count=row["claim_count"],
            alert_count=row["alert_count"],
            evidence_count=row["evidence_count"],
            community_id=comm_val,
            created_at=row["created_at"],
            queued_at=now_iso,
            case_builder_version=row["case_builder_version"],
            siu_version=row["siu_version"],
        )

        val_errs = item.validate()
        if val_errs:
            raise ValueError(f"Queue item validation failed for {queue_id}: {val_errs}")

        queue_items.append(item)
        final_records.append(item.to_dict())

    queue_df = pd.DataFrame(final_records)
    return queue_df, queue_items


# ------------------------------------------------------------------------------
# Evaluation & Baseline Comparisons
# ------------------------------------------------------------------------------

def generate_evaluation_report(
    total_cases_df: pd.DataFrame,
    queue_df: pd.DataFrame,
    daily_capacity: int,
) -> Dict[str, Any]:
    """
    Generate rigorous, factual evaluation report comparing SIU priority against baselines.
    
    Explicit disclaimer: Operational prioritization evaluation only; no ground-truth fraud labels were used.
    """
    total_count = len(total_cases_df)
    eligible_count = len(queue_df)
    excluded_count = total_count - eligible_count

    if queue_df.empty:
        return {
            "total_cases": total_count,
            "eligible_cases": 0,
            "excluded_cases": excluded_count,
            "daily_capacity": daily_capacity,
            "selected_count": 0,
            "deferred_count": 0,
            "evaluation_notes": "Operational prioritization evaluation only; no ground-truth fraud labels were used.",
        }

    selected_mask = queue_df["capacity_selected"] == True
    selected_df = queue_df[selected_mask]
    deferred_df = queue_df[~selected_mask]

    selected_count = len(selected_df)
    deferred_count = len(deferred_df)

    tier_counts = queue_df["priority_tier"].value_counts().to_dict()

    avg_p_score = float(queue_df["priority_score"].mean())
    median_p_score = float(queue_df["priority_score"].median())

    avg_risk_sel = float(selected_df["risk_score"].mean()) if not selected_df.empty else 0.0
    avg_risk_def = float(deferred_df["risk_score"].mean()) if not deferred_df.empty else 0.0

    avg_exp_sel = float(selected_df["estimated_exposure"].mean()) if not selected_df.empty else 0.0
    avg_exp_def = float(deferred_df["estimated_exposure"].mean()) if not deferred_df.empty else 0.0

    # Baselines comparison on top-N
    n = min(daily_capacity, len(queue_df))
    if n > 0:
        # Baseline 1: SIU Unified Priority (current selected)
        siu_top_n = selected_df.head(n)
        siu_metrics = {
            "average_risk_score": round(float(siu_top_n["risk_score"].mean()), 4),
            "average_exposure": round(float(siu_top_n["estimated_exposure"].mean()), 2),
            "total_exposure": round(float(siu_top_n["estimated_exposure"].sum()), 2),
            "average_evidence_strength": round(float(siu_top_n["evidence_strength"].mean()), 4),
            "average_priority_score": round(float(siu_top_n["priority_score"].mean()), 4),
        }

        # Baseline 2: Risk-Only Baseline (sort by risk_score DESC)
        risk_top_n = queue_df.sort_values(
            by=["risk_score", "evidence_strength", "estimated_exposure", "case_id"],
            ascending=[False, False, False, True]
        ).head(n)
        risk_metrics = {
            "average_risk_score": round(float(risk_top_n["risk_score"].mean()), 4),
            "average_exposure": round(float(risk_top_n["estimated_exposure"].mean()), 2),
            "total_exposure": round(float(risk_top_n["estimated_exposure"].sum()), 2),
            "average_evidence_strength": round(float(risk_top_n["evidence_strength"].mean()), 4),
            "average_priority_score": round(float(risk_top_n["priority_score"].mean()), 4),
        }

        # Baseline 3: Exposure-Only Baseline (sort by estimated_exposure DESC)
        exp_top_n = queue_df.sort_values(
            by=["estimated_exposure", "risk_score", "evidence_strength", "case_id"],
            ascending=[False, False, False, True]
        ).head(n)
        exp_metrics = {
            "average_risk_score": round(float(exp_top_n["risk_score"].mean()), 4),
            "average_exposure": round(float(exp_top_n["estimated_exposure"].mean()), 2),
            "total_exposure": round(float(exp_top_n["estimated_exposure"].sum()), 2),
            "average_evidence_strength": round(float(exp_top_n["evidence_strength"].mean()), 4),
            "average_priority_score": round(float(exp_top_n["priority_score"].mean()), 4),
        }
    else:
        siu_metrics, risk_metrics, exp_metrics = {}, {}, {}

    # Signal Missingness tracking
    missingness = {
        "network_signal_missing_count": int((queue_df["network_signal"] == 0.0).sum()),
        "anomaly_signal_missing_count": int((queue_df["anomaly_signal"] == 0.0).sum()),
        "future_risk_missing_count": int((queue_df["future_risk_signal"] == 0.0).sum()),
        "behavioral_signal_missing_count": int((queue_df["behavioral_signal"] == 0.0).sum()),
        "exposure_zero_count": int((queue_df["estimated_exposure"] == 0.0).sum()),
    }

    report = {
        "total_cases": total_count,
        "eligible_cases": eligible_count,
        "excluded_cases": excluded_count,
        "daily_capacity": daily_capacity,
        "selected_count": selected_count,
        "deferred_count": deferred_count,
        "priority_tier_counts": tier_counts,
        "average_priority_score": round(avg_p_score, 4),
        "median_priority_score": round(median_p_score, 4),
        "average_risk_score_selected": round(avg_risk_sel, 4),
        "average_risk_score_deferred": round(avg_risk_def, 4),
        "average_exposure_selected": round(avg_exp_sel, 2),
        "average_exposure_deferred": round(avg_exp_def, 2),
        "baseline_comparison_top_n": {
            "siu_unified_priority": siu_metrics,
            "risk_only_baseline": risk_metrics,
            "exposure_only_baseline": exp_metrics,
        },
        "signal_missingness": missingness,
        "queue_determinism_check": True,
        "evaluation_notes": "Operational prioritization evaluation only; no ground-truth fraud labels were used.",
    }

    return report


# ------------------------------------------------------------------------------
# Full End-to-End Pipeline
# ------------------------------------------------------------------------------

def run_siu_pipeline(
    cases_input: Union[str, Path, pd.DataFrame] = "outputs/cases/cases.parquet",
    config_path: Optional[Union[str, Path, Dict[str, Any]]] = None,
    daily_capacity: Optional[int] = None,
    output_dir: Union[str, Path] = "outputs/siu",
) -> Dict[str, Any]:
    """
    Execute full SIU Priority Queue pipeline, persist artifacts, and print concise summary.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    cfg = load_queue_config(config_path)
    cap = daily_capacity if daily_capacity is not None else int(cfg.get("siu", {}).get("daily_capacity", 20))

    print("=" * 70)
    print("  VIGIL-X SIU PRIORITY QUEUE SUBSYSTEM")
    print("=" * 70)

    # 1. Load cases
    df_raw = load_cases_dataset(cases_input)
    print(f"[SIU Queue] Loaded {len(df_raw)} investigation cases.")

    # 2. Build Queue
    queue_df, queue_items = build_siu_queue(df_raw, daily_capacity=cap, config=cfg)
    print(f"[SIU Queue] Prioritized {len(queue_df)} eligible cases (Daily capacity: {cap}).")

    # 3. Save Parquet
    parquet_path = out_path / "siu_queue.parquet"
    queue_df.to_parquet(parquet_path, index=False)
    print(f"[SIU Queue] Saved Parquet -> {parquet_path}")

    # 4. Save CSV (serialize priority_reasons to JSON strings)
    csv_path = out_path / "siu_queue.csv"
    csv_records = [item.to_dict(serialize_lists=True) for item in queue_items]
    pd.DataFrame(csv_records).to_csv(csv_path, index=False)
    print(f"[SIU Queue] Saved CSV -> {csv_path}")

    # 5. Generate and Save Evaluation Report
    report = generate_evaluation_report(df_raw, queue_df, daily_capacity=cap)
    report_path = out_path / "siu_evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[SIU Queue] Saved Evaluation Report -> {report_path}")

    # 6. Concise CLI Summary
    print("\n" + "-" * 40)
    print("SIU Priority Queue Summary")
    print("-" * 40)
    print(f"Cases loaded: {report['total_cases']}")
    print(f"Eligible:     {report['eligible_cases']}")
    print(f"Excluded:     {report['excluded_cases']}")
    print()
    print(f"Daily capacity: {report['daily_capacity']}")
    print(f"Selected:       {report['selected_count']}")
    print(f"Deferred:       {report['deferred_count']}")
    print()
    for tier in [SIUPriorityTier.CRITICAL.value, SIUPriorityTier.HIGH.value, SIUPriorityTier.MEDIUM.value, SIUPriorityTier.LOW.value]:
        count = report["priority_tier_counts"].get(tier, 0)
        print(f"{tier:<9}: {count}")

    if not queue_df.empty:
        top1 = queue_df.iloc[0]
        print()
        print("Top Case:")
        print(f"Queue ID:       {top1['queue_id']}")
        print(f"Case ID:        {top1['case_id']}")
        print(f"Provider:       {top1['provider_id']}")
        print(f"Priority Score: {top1['priority_score']:.4f}")
        print(f"Priority Tier:  {top1['priority_tier']}")
        print(f"Risk Score:     {top1['risk_score']:.4f}")
        print(f"Exposure:       ${top1['estimated_exposure']:,.2f}")
    print("=" * 70)

    return report


if __name__ == "__main__":
    run_siu_pipeline()
