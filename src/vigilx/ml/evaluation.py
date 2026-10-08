"""
Phase 1 ML evaluation for Vigil-X.

Computes:
  - ROC-AUC
  - PR-AUC (Average Precision)
  - Precision@K, Recall@K for K in [10, 25, 50, 100]
  - Positive / negative counts
  - Per-fold breakdown
  - Baseline comparisons (amount-only, prediction-count-only)

EVALUATION PHILOSOPHY
=====================
Because fraudulent claims represent < 1% of the data, ROC-AUC alone
is misleading (it is dominated by the large negative class). We
primarily report PR-AUC and Precision@K because:
  - PR curves focus on the minority positive class.
  - SIU investigators work a fixed case queue → P@K and R@K directly
    measure whether the model surfaces true positives at the top of the
    ranked list.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    from sklearn.metrics import (
        average_precision_score,
        roc_auc_score,
    )
except ImportError as exc:
    raise ImportError("scikit-learn required for evaluation.") from exc

from vigilx.ml.oof import FoldInfo


# ------------------------------------------------------------------
# Core metric helpers
# ------------------------------------------------------------------


def precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of true positives in the top-K scored claims."""
    if k <= 0 or len(y_true) == 0:
        return 0.0
    k = min(k, len(y_true))
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true[top_k_idx].sum()) / k


def recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of all true positives captured in the top-K scored claims."""
    if k <= 0 or len(y_true) == 0:
        return 0.0
    total_positive = y_true.sum()
    if total_positive == 0:
        return 0.0
    k = min(k, len(y_true))
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true[top_k_idx].sum()) / float(total_positive)


def compute_average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """
    Compute uninterpolated average precision (PR-AUC) robustly.

    Avoids Python 3.14 borrowed-refcount memory reuse bug in scikit-learn
    where binary_op (+) mutates tps in-place for arrays >= 32,768 elements.
    """
    desc_indices = np.argsort(y_score, kind="mergesort")[::-1]
    y_true_sorted = y_true[desc_indices]
    tps = np.cumsum(y_true_sorted)
    n_pos = tps[-1]
    if n_pos == 0:
        return 0.0
    ranks = np.arange(1, len(y_true) + 1)
    precisions = tps / ranks
    return float(np.sum(precisions * y_true_sorted) / n_pos)


def compute_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    ks: list[int] | None = None,
    label: str = "",
) -> dict:
    """
    Compute all Phase 1 evaluation metrics.

    Parameters
    ----------
    y_true : ndarray of {0, 1}
    y_score : ndarray of float (predicted probability or score)
    ks : list of K values for P@K and R@K
    label : optional label for display

    Returns
    -------
    dict with all metrics
    """
    if ks is None:
        ks = [10, 25, 50, 100]

    n = len(y_true)
    pos = int(y_true.sum())
    neg = n - pos

    result: dict = {
        "label": label,
        "n_claims": n,
        "n_positives": pos,
        "n_negatives": neg,
        "positive_rate": round(pos / n, 6) if n > 0 else 0.0,
    }

    if pos == 0:
        result.update({
            "roc_auc": None,
            "pr_auc": None,
            **{f"precision_at_{k}": None for k in ks},
            **{f"recall_at_{k}": None for k in ks},
            **{f"rank_lift_at_{k}": None for k in ks},
        })
        return result

    base_rate = pos / n if n > 0 else 0.0

    if len(np.unique(y_true)) < 2:
        res_update = {
            "roc_auc": None,
            "pr_auc": None,
        }
        for k in ks:
            p_at_k = precision_at_k(y_true, y_score, k)
            res_update[f"precision_at_{k}"] = round(p_at_k, 4)
            res_update[f"recall_at_{k}"] = round(recall_at_k(y_true, y_score, k), 4)
            res_update[f"rank_lift_at_{k}"] = round(p_at_k / base_rate, 2) if base_rate > 0 else 0.0
        result.update(res_update)
        return result

    result["roc_auc"] = round(roc_auc_score(y_true, y_score), 4)
    result["pr_auc"] = round(compute_average_precision(y_true, y_score), 4)

    for k in ks:
        p_at_k = precision_at_k(y_true, y_score, k)
        result[f"precision_at_{k}"] = round(p_at_k, 4)
        result[f"recall_at_{k}"] = round(recall_at_k(y_true, y_score, k), 4)
        result[f"rank_lift_at_{k}"] = round(p_at_k / base_rate, 2) if base_rate > 0 else 0.0

    return result


# ------------------------------------------------------------------
# Baseline scorers
# ------------------------------------------------------------------


def baseline_amount_scorer(claims: pd.DataFrame) -> np.ndarray:
    """
    Baseline 1 — Rank claims by paid_amount (descending).
    Hypothesis: fraudulent claims tend to be high-dollar.
    """
    col = "paid_amount" if "paid_amount" in claims.columns else "billed_amount"
    return pd.to_numeric(claims[col], errors="coerce").fillna(0.0).values


def baseline_random_scorer(n: int, seed: int = 42) -> np.ndarray:
    """Baseline 0 — Random ranking (lower bound)."""
    rng = np.random.RandomState(seed)
    return rng.rand(n)


# ------------------------------------------------------------------
# Full evaluation report
# ------------------------------------------------------------------


def evaluate_claim_model(
    claim_ml: pd.DataFrame,
    claims: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
    fold_infos: list[FoldInfo],
    output_dir: Optional[str | Path] = None,
    ks: list[int] | None = None,
) -> dict:
    """
    Produce a complete ML evaluation report.

    Parameters
    ----------
    claim_ml : DataFrame with 'claim_id', 'provider_id', 'ml_probability', 'oof_fold'
               and optionally 'calibrated_probability'
    claims : original claims DataFrame
    gt_claim_labels : ground truth
    fold_infos : list of FoldInfo from OOF training
    output_dir : if provided, save report as evaluation_report.json

    Returns
    -------
    dict containing metrics for model and baselines
    """
    if ks is None:
        ks = [10, 25, 50, 100]

    # Merge ground truth onto predictions
    label_map = (
        gt_claim_labels[["claim_id", "is_suspicious"]]
        .drop_duplicates("claim_id")
        .set_index("claim_id")["is_suspicious"]
    )
    claim_ml = claim_ml.copy()
    claim_ml["y_true"] = claim_ml["claim_id"].map(label_map).fillna(0).astype(int)

    y_true = claim_ml["y_true"].values
    y_score = claim_ml["ml_probability"].values.astype(float)

    # Merge paid_amount for baseline
    if "paid_amount" in claims.columns:
        paid = claims[["claim_id", "paid_amount"]].copy()
        claim_ml = claim_ml.merge(paid, on="claim_id", how="left")
    else:
        claim_ml["paid_amount"] = 0.0

    y_amount = claim_ml["paid_amount"].fillna(0.0).values.astype(float)
    y_random = baseline_random_scorer(len(y_true))

    # Compute metrics for raw LightGBM scores
    model_metrics = compute_metrics(y_true, y_score, ks=ks, label="LightGBM OOF")
    baseline_amount = compute_metrics(y_true, y_amount, ks=ks, label="Baseline: Amount-Only")
    baseline_random = compute_metrics(y_true, y_random, ks=ks, label="Baseline: Random")

    # Calibration metrics (Phase 2) — present when calibrated_probability column exists
    calibration_metrics: Optional[dict] = None
    if "calibrated_probability" in claim_ml.columns:
        y_cal = claim_ml["calibrated_probability"].values.astype(float)
        cal_model_metrics = compute_metrics(y_true, y_cal, ks=ks, label="LightGBM OOF Calibrated")
        from vigilx.ml.calibration import evaluate_calibration as _eval_cal
        calibration_metrics = _eval_cal(y_true, y_score, y_cal)
        calibration_metrics["calibrated_model"] = cal_model_metrics

    # Per-fold breakdown
    fold_metrics = []
    for fi in fold_infos:
        fold_mask = claim_ml["oof_fold"] == fi.fold
        fm_true = y_true[fold_mask]
        fm_score = y_score[fold_mask]
        fm = compute_metrics(fm_true, fm_score, ks=[10, 25], label=f"Fold {fi.fold}")
        fm["n_val_providers"] = len(fi.val_providers)
        fm["val_positive_rate"] = fi.val_positive_rate
        fold_metrics.append(fm)

    # Provider-level summary
    provider_summary = (
        claim_ml.groupby("provider_id")
        .agg(
            n_claims=("claim_id", "count"),
            mean_ml_score=("ml_probability", "mean"),
            max_ml_score=("ml_probability", "max"),
            n_suspicious_gt=("y_true", "sum"),
        )
        .reset_index()
    )
    n_providers = len(provider_summary)
    n_suspicious_providers = int((provider_summary["n_suspicious_gt"] > 0).sum())

    report = {
        "evaluation_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "n_claims": int(len(claim_ml)),
        "n_providers": n_providers,
        "n_suspicious_providers_in_gt": n_suspicious_providers,
        "n_folds": len(fold_infos),
        "model": model_metrics,
        "baseline_amount": baseline_amount,
        "baseline_random": baseline_random,
        "per_fold": fold_metrics,
    }
    if calibration_metrics is not None:
        report["calibration"] = calibration_metrics

    # Pretty print summary
    _print_report(report)

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "evaluation_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[Evaluation] Report saved → {report_path}")

    return report



def _print_report(report: dict) -> None:
    """Print a concise evaluation summary to stdout."""
    sep = "=" * 60
    print(f"\n{sep}")
    print("  VIGIL-X ML EVALUATION REPORT")
    print(sep)
    print(f"  Claims: {report['n_claims']:,}  |  Providers: {report['n_providers']:,}")
    print(f"  Suspicious GT providers: {report['n_suspicious_providers_in_gt']}")
    print(f"  OOF Folds: {report['n_folds']}")
    print(sep)

    for name, m in [
        ("LightGBM OOF", report["model"]),
        ("Baseline: Amount-Only", report["baseline_amount"]),
        ("Baseline: Random", report["baseline_random"]),
    ]:
        roc = m.get("roc_auc", "N/A")
        pr = m.get("pr_auc", "N/A")
        p50 = m.get("precision_at_50", "N/A")
        r50 = m.get("recall_at_50", "N/A")
        lift50 = m.get("rank_lift_at_50", "N/A")
        print(f"  [{name}]")
        print(f"    ROC-AUC={roc}  PR-AUC={pr}  P@50={p50}  R@50={r50}  Lift@50={lift50}x")

    # Calibration summary (Phase 2)
    cal = report.get("calibration")
    if cal:
        cal_m = cal.get("calibrated_model", {})
        brier_b = cal.get("brier_score", {}).get("before", "N/A")
        brier_a = cal.get("brier_score", {}).get("after", "N/A")
        ece_b = cal.get("expected_calibration_error", {}).get("before", "N/A")
        ece_a = cal.get("expected_calibration_error", {}).get("after", "N/A")
        print(f"  [Calibration]")
        print(f"    Brier before={brier_b}  after={brier_a}")
        print(f"    ECE   before={ece_b}  after={ece_a}")
        pr_cal = cal_m.get("pr_auc", "N/A")
        roc_cal = cal_m.get("roc_auc", "N/A")
        print(f"    Calibrated ROC-AUC={roc_cal}  PR-AUC={pr_cal}")

    print(sep)
    print("  Per-Fold Summary:")
    for fm in report.get("per_fold", []):
        label = fm.get("label", "")
        roc = fm.get("roc_auc", "N/A")
        pr = fm.get("pr_auc", "N/A")
        pos = fm.get("n_positives", 0)
        n = fm.get("n_claims", 0)
        print(f"    {label}: ROC={roc}  PR={pr}  pos={pos}/{n}")
    print(f"{sep}\n")
