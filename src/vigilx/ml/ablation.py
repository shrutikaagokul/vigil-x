"""
Feature group ablation study for Vigil-X claim-level risk model.

Systematically evaluates the contribution of individual feature groups
by retraining provider-grouped OOF models with specific groups ablated (held out):
  1. Full Model (All Features)
  2. Without Temporal Rolling Features
  3. Without Provider Utilization Features
  4. Without Member Utilization Features
  5. Without Geographic Features
  6. Claim Base Features Only (No behavioral / historical features)

SCIENTIFIC PRINCIPLES:
  - Identical folds across all ablation variants (apples-to-apples comparison).
  - Strict provider grouping in every variant (no leakage).
  - Standardized metrics: PR-AUC, ROC-AUC, Precision@50, Recall@50, Rank-Lift@50.
  - Reports delta relative to Full Model to isolate marginal value.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from vigilx.ml.claim_features_ml import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_claim_feature_matrix,
)
from vigilx.ml.claim_model import ClaimRiskModel, prepare_target
from vigilx.ml.evaluation import compute_metrics
from vigilx.ml.oof import provider_grouped_kfold

# Feature group definitions matching claim_features_ml
TEMPORAL_FEATURES = [
    "rolling_7d_claims",
    "rolling_30d_claims",
    "rolling_90d_claims",
    "rolling_30d_dollars",
]

PROVIDER_UTIL_FEATURES = [
    "provider_total_claims",
    "provider_unique_members",
    "provider_total_paid",
    "provider_visits_per_member",
    "provider_em_45_share",
    "provider_specialty",
]

MEMBER_UTIL_FEATURES = [
    "member_total_claims",
    "member_unique_providers",
    "member_unique_cpts",
    "member_days_since_last_claim",
]

GEO_FEATURES = [
    "dist_member_provider_miles",
]

CLAIM_BASE_FEATURES = [
    col
    for col in ALL_FEATURES
    if col not in (TEMPORAL_FEATURES + PROVIDER_UTIL_FEATURES + MEMBER_UTIL_FEATURES + GEO_FEATURES)
]

ABLATION_EXPERIMENTS: dict[str, list[str]] = {
    "full_model": ALL_FEATURES,
    "no_temporal": [f for f in ALL_FEATURES if f not in TEMPORAL_FEATURES],
    "no_provider_util": [f for f in ALL_FEATURES if f not in PROVIDER_UTIL_FEATURES],
    "no_member_util": [f for f in ALL_FEATURES if f not in MEMBER_UTIL_FEATURES],
    "no_geo": [f for f in ALL_FEATURES if f not in GEO_FEATURES],
    "claim_base_only": CLAIM_BASE_FEATURES,
}


def run_ablation_study(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    members: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
    n_folds: int = 5,
    random_state: int = 42,
    output_dir: Optional[str | Path] = None,
    experiments: Optional[dict[str, list[str]]] = None,
) -> dict[str, Any]:
    """
    Run ablation experiments using identical provider folds across all variants.

    Parameters
    ----------
    claims : DataFrame of claims
    providers : DataFrame of providers
    members : DataFrame of members
    gt_claim_labels : DataFrame of ground truth labels
    n_folds : number of provider-grouped folds
    random_state : seed for reproducibility
    output_dir : optional directory to save ablation_report.json
    experiments : optional dict mapping experiment name -> feature list

    Returns
    -------
    dict with full ablation comparison and relative deltas
    """
    if experiments is None:
        experiments = ABLATION_EXPERIMENTS

    print("[Ablation] Assembling base feature matrix...")
    feat_matrix = build_claim_feature_matrix(claims, providers, members)
    y = prepare_target(feat_matrix, gt_claim_labels)
    provider_ids = feat_matrix["provider_id"]

    # Pre-generate fixed fold assignments so all ablations evaluate on identical splits
    splits = [
        (tr, va)
        for tr, va, _ in provider_grouped_kfold(
            feat_matrix, y, provider_ids, n_splits=n_folds, random_state=random_state
        )
    ]

    results: dict[str, Any] = {}
    full_metrics: Optional[dict[str, Any]] = None

    for exp_name, feat_cols in experiments.items():
        print(f"[Ablation] Evaluating '{exp_name}' with {len(feat_cols)} features...")
        X_exp = feat_matrix[feat_cols]

        oof_probs = np.zeros(len(y), dtype=np.float32)

        for train_idx, val_idx in splits:
            X_tr, y_tr = X_exp.iloc[train_idx], y[train_idx]
            X_va, y_va = X_exp.iloc[val_idx], y[val_idx]

            model = ClaimRiskModel(n_folds=1, random_state=random_state)
            # Train fold
            fit_kwargs: dict[str, Any] = {}
            cat_in_exp = [c for c in CATEGORICAL_FEATURES if c in feat_cols]
            if cat_in_exp:
                fit_kwargs["categorical_feature"] = cat_in_exp

            model.train_final(X_tr, y_tr)
            oof_probs[val_idx] = model.predict_proba(X_va)

        m = compute_metrics(y, oof_probs, ks=[10, 25, 50, 100], label=exp_name)
        m["n_features"] = len(feat_cols)
        m["features"] = feat_cols

        if exp_name == "full_model":
            full_metrics = m
            m["delta_pr_auc"] = 0.0
            m["delta_roc_auc"] = 0.0
        else:
            base_pr = full_metrics["pr_auc"] if full_metrics and full_metrics["pr_auc"] else 0.0
            base_roc = full_metrics["roc_auc"] if full_metrics and full_metrics["roc_auc"] else 0.0
            m["delta_pr_auc"] = round((m["pr_auc"] or 0.0) - base_pr, 4)
            m["delta_roc_auc"] = round((m["roc_auc"] or 0.0) - base_roc, 4)

        results[exp_name] = m

    report = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "n_claims": len(claims),
        "n_providers": len(providers),
        "n_folds": n_folds,
        "experiments": results,
    }

    _print_ablation_summary(report)

    if output_dir is not None:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        report_file = out_path / "ablation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[Ablation] Report saved → {report_file}")

    return report


def _print_ablation_summary(report: dict[str, Any]) -> None:
    """Print formatted ablation summary table."""
    sep = "=" * 80
    print(f"\n{sep}")
    print("  VIGIL-X FEATURE ABLATION STUDY")
    print(sep)
    print(f"{'Experiment':<22} | {'Feats':<5} | {'PR-AUC':<8} | {'Δ PR-AUC':<9} | {'ROC-AUC':<8} | {'P@50':<6} | {'Lift@50':<8}")
    print("-" * 80)
    for name, exp in report.get("experiments", {}).items():
        n_f = exp.get("n_features", 0)
        pr = exp.get("pr_auc", "N/A")
        d_pr = f"{exp.get('delta_pr_auc', 0.0):+.4f}" if "delta_pr_auc" in exp else "0.0000"
        roc = exp.get("roc_auc", "N/A")
        p50 = exp.get("precision_at_50", "N/A")
        lift = f"{exp.get('rank_lift_at_50', 'N/A')}x"
        print(f"{name:<22} | {n_f:<5} | {pr:<8} | {d_pr:<9} | {roc:<8} | {p50:<6} | {lift:<8}")
    print(f"{sep}\n")
