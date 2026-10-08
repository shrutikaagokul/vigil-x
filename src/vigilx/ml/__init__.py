"""
Vigil-X ML + Risk Intelligence subsystem.

Capabilities:
  - Claim Risk Modeling: LightGBM with provider-grouped out-of-fold cross validation
  - Calibration: Isotonic probability calibration fitted strictly on OOF predictions
  - Explainability: Native TreeSHAP attribution and top risk driver extraction
  - Provider Anomaly Detection: Unsupervised Isolation Forest on behavioral feature profiles
  - Future Risk Forecasting: 30/60/90-day provider forward risk prediction
  - Comprehensive Evaluation: PR-AUC, ROC-AUC, P@K, R@K, rank lift, and baseline comparisons
  - Ablation Studies: Empirical feature group attribution
"""
from vigilx.ml.ablation import run_ablation_study
from vigilx.ml.calibration import (
    IsotonicCalibrator,
    calibrate_oof,
    evaluate_calibration,
)
from vigilx.ml.claim_features_ml import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_claim_feature_matrix,
)
from vigilx.ml.claim_model import (
    ClaimRiskModel,
    train_and_predict,
)
from vigilx.ml.evaluation import (
    compute_metrics,
    evaluate_claim_model,
    precision_at_k,
    recall_at_k,
)
from vigilx.ml.explainability import (
    TreeSHAPExplainer,
    batch_extract_top_features,
    compute_oof_shap,
    format_claim_explanation,
)
from vigilx.ml.future_risk import (
    FutureRiskModel,
    evaluate_future_risk,
    train_and_predict_future_risk,
)
from vigilx.ml.provider_anomaly import (
    ProviderAnomalyDetector,
    evaluate_provider_anomaly,
    train_and_detect,
)

__all__ = [
    "ALL_FEATURES",
    "CATEGORICAL_FEATURES",
    "NUMERIC_FEATURES",
    "ClaimRiskModel",
    "FutureRiskModel",
    "IsotonicCalibrator",
    "ProviderAnomalyDetector",
    "TreeSHAPExplainer",
    "batch_extract_top_features",
    "build_claim_feature_matrix",
    "calibrate_oof",
    "compute_metrics",
    "compute_oof_shap",
    "evaluate_calibration",
    "evaluate_claim_model",
    "evaluate_future_risk",
    "evaluate_provider_anomaly",
    "format_claim_explanation",
    "precision_at_k",
    "recall_at_k",
    "run_ablation_study",
    "train_and_detect",
    "train_and_predict",
    "train_and_predict_future_risk",
]
