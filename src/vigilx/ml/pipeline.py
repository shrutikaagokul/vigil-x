"""
Complete ML Intelligence Subsystem Pipeline runner for Vigil-X.

Runs all components end-to-end:
  1. Claim Risk Modeling: LightGBM with provider-grouped OOF cross-validation
  2. Probability Calibration: Isotonic calibration fitted strictly on OOF predictions
  3. Explainability: TreeSHAP attribution and top risk driver extraction
  4. Provider Anomaly Detection: Unsupervised Isolation Forest on behavioral profiles
  5. Future Risk Forecasting: 30/60/90-day provider forward risk prediction
  6. Evaluation & Baselines: PR-AUC, ROC-AUC, P@K, R@K, rank lift vs baselines
  7. Optional Ablation Study: Feature group marginal value analysis

Usage:
    python -m vigilx.ml.pipeline [--output-dir OUTPUT_DIR] [--run-ablation]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from vigilx.ml.ablation import run_ablation_study
from vigilx.ml.claim_model import train_and_predict
from vigilx.ml.evaluation import evaluate_claim_model
from vigilx.ml.future_risk import (
    evaluate_future_risk,
    train_and_predict_future_risk,
)
from vigilx.ml.provider_anomaly import (
    evaluate_provider_anomaly,
    train_and_detect,
)


def run(
    output_dir: str = "outputs/phase2",
    n_providers: int = 1200,
    n_members: int = 25000,
    n_facilities: int = 110,
    n_months: int = 24,
    n_claims: int | None = None,
    seed: int = 42,
    n_folds: int = 5,
    run_ablation: bool = False,
) -> dict[str, Any]:
    """
    Run the complete ML intelligence subsystem end-to-end.

    Returns comprehensive multi-model evaluation reports dict.
    """
    try:
        from generator.synthetic_data import generate_synthetic_data
    except ImportError:
        from importlib import import_module
        generate_synthetic_data = import_module("generator.synthetic_data").generate_synthetic_data

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  VIGIL-X COMPLETE ML SUBSYSTEM PIPELINE")
    print("=" * 70)
    print(f"[Pipeline] Generating synthetic data "
          f"(providers={n_providers}, members={n_members}, seed={seed})...")
    data = generate_synthetic_data(
        n_providers=n_providers,
        n_members=n_members,
        n_facilities=n_facilities,
        n_months=n_months,
        n_claims=n_claims,
        seed=seed,
    )

    claims = data["claims"]
    providers = data["providers"]
    members = data["members"]
    gt_claim_labels = data["gt_claim_labels"]
    gt_entity_labels = data["gt_entity_labels"]

    print(f"[Pipeline] Ingested {len(claims):,} claims, "
          f"{len(providers):,} providers, "
          f"{len(members):,} members")
    print(f"[Pipeline] Ground truth suspicious claims: {gt_claim_labels['is_suspicious'].sum():,}")

    # --------------------------------------------------------------
    # 1. Claim Risk Modeling + Calibration + TreeSHAP
    # --------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  PHASE A: CLAIM-LEVEL RISK MODEL (LIGHTGBM + CALIBRATION + SHAP)")
    print("-" * 70)
    claim_ml, claim_model, fold_infos = train_and_predict(
        claims=claims,
        providers=providers,
        members=members,
        gt_claim_labels=gt_claim_labels,
        output_dir=output_dir,
        n_folds=n_folds,
        random_state=seed,
    )

    claim_report = evaluate_claim_model(
        claim_ml=claim_ml,
        claims=claims,
        gt_claim_labels=gt_claim_labels,
        fold_infos=fold_infos,
        output_dir=output_dir,
    )

    # --------------------------------------------------------------
    # 2. Provider Behavioral Anomaly Detection (Isolation Forest)
    # --------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  PHASE B: PROVIDER BEHAVIORAL ANOMALY DETECTION (ISOLATION FOREST)")
    print("-" * 70)
    provider_anomaly, anomaly_detector = train_and_detect(
        claims=claims,
        providers=providers,
        output_dir=output_dir,
        random_state=seed,
    )

    anomaly_report = evaluate_provider_anomaly(
        provider_anomaly=provider_anomaly,
        gt_entity_labels=gt_entity_labels,
    )
    anomaly_eval_path = output_dir / "provider_anomaly_eval.json"
    with open(anomaly_eval_path, "w") as f:
        json.dump(anomaly_report, f, indent=2, default=str)
    print(f"[Pipeline] Provider anomaly evaluation saved → {anomaly_eval_path}")

    # --------------------------------------------------------------
    # 3. Future Risk Forecasting (30 / 60 / 90 Days)
    # --------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  PHASE C: FUTURE RISK FORECASTING (30 / 60 / 90 DAYS)")
    print("-" * 70)
    future_risk, risk_models, risk_train_reports = train_and_predict_future_risk(
        claims=claims,
        providers=providers,
        gt_entity_labels=gt_entity_labels,
        output_dir=output_dir,
        random_state=seed,
    )

    future_risk_report = evaluate_future_risk(
        future_risk=future_risk,
        gt_entity_labels=gt_entity_labels,
    )
    future_eval_path = output_dir / "future_risk_eval.json"
    with open(future_eval_path, "w") as f:
        json.dump(future_risk_report, f, indent=2, default=str)
    print(f"[Pipeline] Future risk evaluation saved → {future_eval_path}")

    # --------------------------------------------------------------
    # 4. Optional Ablation Study
    # --------------------------------------------------------------
    ablation_report: Optional[dict[str, Any]] = None
    if run_ablation:
        print("\n" + "-" * 70)
        print("  FEATURE GROUP ABLATION STUDY")
        print("-" * 70)
        ablation_report = run_ablation_study(
            claims=claims,
            providers=providers,
            members=members,
            gt_claim_labels=gt_claim_labels,
            n_folds=n_folds,
            random_state=seed,
            output_dir=output_dir,
        )

    full_summary = {
        "claim_evaluation": claim_report,
        "provider_anomaly_evaluation": anomaly_report,
        "future_risk_evaluation": future_risk_report,
        "ablation_report": ablation_report,
    }

    print("\n" + "=" * 70)
    print("  ALL ML SUBSYSTEM ARTIFACTS GENERATED SUCCESSFULLY")
    print(f"  Artifacts directory: {output_dir.resolve()}")
    print("=" * 70)
    return full_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Vigil-X Complete ML Pipeline")
    parser.add_argument("--output-dir", default="outputs/phase2", help="Output directory")
    parser.add_argument("--n-claims", type=int, default=None, help="Override claim count")
    parser.add_argument("--n-folds", type=int, default=5, help="OOF folds")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--run-ablation", action="store_true", help="Run feature ablation study")
    args = parser.parse_args()

    run(
        output_dir=args.output_dir,
        n_claims=args.n_claims,
        n_folds=args.n_folds,
        seed=args.seed,
        run_ablation=args.run_ablation,
    )


if __name__ == "__main__":
    main()
