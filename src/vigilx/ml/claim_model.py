"""
LightGBM claim-level risk model for Vigil-X.

This module provides:
  - ClaimRiskModel: LightGBM binary classifier with provider-grouped OOF,
    isotonic probability calibration, and TreeSHAP explainability
  - train_and_predict: End-to-end training, OOF calibration, and SHAP pipeline
  - MODEL_VERSION / FEATURE_VERSION metadata

DESIGN NOTES
============
Terminology:
  - "ml_risk_score"          — raw LightGBM probability output (uncalibrated)
  - "ml_probability"         — alias for raw LightGBM probability
  - "calibrated_probability" — isotonic regression calibrated probability fitted
                               strictly on out-of-fold predictions
  - "ml_prediction"          — binary decision flag based on calibrated probability

Class Imbalance:
  The positive class (suspicious claims) represents ~0.3% of all claims.
  LightGBM's `is_unbalance=True` automatically adjusts the positive class
  weight to `neg_count / pos_count`. This avoids the model collapsing to
  predict all-zero. We additionally use early stopping on the validation
  fold to prevent overfitting.

Calibration (Phase 2):
  Raw tree model outputs with `is_unbalance=True` are intentionally uncalibrated
  to allow optimal ranking. Isotonic regression maps these raw scores to
  calibrated posterior probabilities without distorting monotonicity,
  using provider-grouped out-of-fold predictions to prevent leakage.

Explainability (Phase 2):
  TreeSHAP attributions are computed via LightGBM's native C++ implementation
  (pred_contrib=True). Each claim receives top contributing risk features
  with exact signed Shapley values.
"""
from __future__ import annotations

import json
import pickle
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb
except ImportError as exc:
    raise ImportError(
        "lightgbm is required. Install with: pip install 'lightgbm>=4.0'"
    ) from exc

from vigilx.ml.calibration import (
    IsotonicCalibrator,
    calibrate_oof,
    fit_final_calibrator,
)
from vigilx.ml.claim_features_ml import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    FEATURE_VERSION,
    NUMERIC_FEATURES,
    build_claim_feature_matrix,
)
from vigilx.ml.explainability import (
    TreeSHAPExplainer,
    batch_extract_top_features,
    compute_oof_shap,
    format_claim_explanation,
)
from vigilx.ml.oof import (
    N_FOLDS,
    FoldInfo,
    generate_oof_predictions,
    validate_oof_integrity,
)


# ------------------------------------------------------------------
# Versioning
# ------------------------------------------------------------------

MODEL_VERSION = "1.0.0"

# ------------------------------------------------------------------
# Default LightGBM hyperparameters
# ------------------------------------------------------------------

DEFAULT_LGBM_PARAMS: dict[str, Any] = {
    "objective": "binary",
    "metric": ["binary_logloss", "auc"],
    "num_leaves": 63,
    "max_depth": -1,               # unlimited; controlled by num_leaves
    "min_child_samples": 50,       # prevents tiny leaf overfitting
    "learning_rate": 0.05,
    "n_estimators": 200,           # sensible baseline for ~150k claims
    "lambda_l1": 0.1,              # L1 regularisation
    "lambda_l2": 0.1,              # L2 regularisation
    "feature_fraction": 0.8,       # subsample features per tree
    "bagging_fraction": 0.8,       # subsample rows per tree
    "bagging_freq": 1,
    "is_unbalance": True,          # handles ~0.3% positive rate automatically
    "verbose": -1,
    "seed": 42,
    "deterministic": True,         # deterministic split finding
    "force_row_wise": True,        # consistent across thread counts
}


# ------------------------------------------------------------------
# Model class
# ------------------------------------------------------------------


class ClaimRiskModel:
    """
    LightGBM binary risk model for claim-level FWA detection.

    Workflow:
        1. Call fit_oof() to train via provider-grouped OOF and obtain
           out-of-fold probability scores for all training claims.
        2. Call calibrate_oof() to obtain leakage-free calibrated probabilities.
        3. Call predict() / predict_calibrated() on new claims for inference.
        4. Call explain() for TreeSHAP explanations.
        5. Call save() / load() for persistence.

    Output convention:
        ml_probability         — LightGBM raw probability (0–1, uncalibrated)
        calibrated_probability — Isotonic calibrated posterior probability
        ml_prediction          — 1 if calibrated_probability >= threshold else 0
    """

    def __init__(
        self,
        params: Optional[dict[str, Any]] = None,
        n_folds: int = N_FOLDS,
        decision_threshold: float = 0.5,
        random_state: int = 42,
    ) -> None:
        self.params = {**DEFAULT_LGBM_PARAMS, **(params or {})}
        self.n_folds = n_folds
        self.decision_threshold = decision_threshold
        self.random_state = random_state

        self._fold_models: list[lgb.LGBMClassifier] = []
        self._fold_infos: list[FoldInfo] = []
        self._feature_names: list[str] = []
        self._is_fitted: bool = False

        # Phase 2 additions
        self.calibrator: Optional[IsotonicCalibrator] = None
        self.fold_calibrators: list[IsotonicCalibrator] = []
        self.explainer: Optional[TreeSHAPExplainer] = None
        self.oof_calibrated_probs: Optional[np.ndarray] = None
        self.oof_shap_values: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit_oof(
        self,
        feature_matrix: pd.DataFrame,
        y: np.ndarray,
        provider_ids: pd.Series,
    ) -> np.ndarray:
        """
        Train via provider-grouped OOF and return OOF raw probabilities.
        """
        X = feature_matrix[ALL_FEATURES].copy()
        self._feature_names = ALL_FEATURES

        cat_colnames = [c for c in CATEGORICAL_FEATURES if c in ALL_FEATURES]

        def _train(X_train: pd.DataFrame, y_train: np.ndarray) -> lgb.LGBMClassifier:
            model = lgb.LGBMClassifier(**self.params)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(
                    X_train, y_train,
                    categorical_feature=cat_colnames,
                )
            return model

        def _predict(model: lgb.LGBMClassifier, X_val: pd.DataFrame) -> np.ndarray:
            return model.predict_proba(X_val)[:, 1]

        oof_probs, fold_infos, fold_models = generate_oof_predictions(
            X, y, provider_ids,
            train_fn=_train,
            predict_fn=_predict,
            n_splits=self.n_folds,
            random_state=self.random_state,
        )

        self._fold_models = fold_models
        self._fold_infos = fold_infos
        self._is_fitted = True

        return oof_probs

    def train_final(
        self,
        feature_matrix: pd.DataFrame,
        y: np.ndarray,
    ) -> None:
        """
        Train a single final model on the entire dataset (for production inference).
        The OOF models are used for evaluation; the final model is for prediction.
        """
        feat_cols = [c for c in ALL_FEATURES if c in feature_matrix.columns]
        if not feat_cols:
            feat_cols = list(feature_matrix.columns)
        self._final_features = feat_cols

        X = feature_matrix[feat_cols].copy()
        cat_colnames = [c for c in CATEGORICAL_FEATURES if c in feat_cols]
        self._final_model = lgb.LGBMClassifier(**self.params)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._final_model.fit(
                X,
                y,
                categorical_feature=cat_colnames if cat_colnames else "auto",
            )

        # Initialise final model TreeSHAP explainer
        self.explainer = TreeSHAPExplainer(self._final_model, feat_cols)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, feature_matrix: pd.DataFrame) -> np.ndarray:
        """Return raw probability scores from the final model."""
        if not hasattr(self, "_final_model"):
            raise RuntimeError(
                "Call train_final() before predict(). "
                "OOF fold models are for evaluation only."
            )
        feat_cols = getattr(self, "_final_features", ALL_FEATURES)
        X = feature_matrix[feat_cols].copy()
        return self._final_model.predict_proba(X)[:, 1]

    def predict_proba(self, feature_matrix: pd.DataFrame) -> np.ndarray:
        """Alias for predict() returning probability scores."""
        return self.predict(feature_matrix)

    def predict_calibrated(self, feature_matrix: pd.DataFrame) -> np.ndarray:
        """
        Return calibrated probabilities from the final model + final calibrator.
        """
        raw_probs = self.predict(feature_matrix)
        if self.calibrator is not None:
            return self.calibrator.predict(raw_probs)
        return raw_probs

    def explain(
        self,
        feature_matrix: pd.DataFrame,
        top_k: int = 4,
    ) -> tuple[np.ndarray, float]:
        """
        Compute TreeSHAP attributions using the final model explainer.
        """
        feat_cols = getattr(self, "_final_features", ALL_FEATURES)
        if self.explainer is None:
            if hasattr(self, "_final_model"):
                self.explainer = TreeSHAPExplainer(self._final_model, feat_cols)
            else:
                raise RuntimeError("Model must be trained with train_final() before explaining.")
        return self.explainer.compute_shap_values(feature_matrix)

    def predict_oof_ensemble(self, feature_matrix: pd.DataFrame) -> np.ndarray:
        """Average predictions across all OOF fold models."""
        if not self._fold_models:
            raise RuntimeError("No fold models found. Call fit_oof() first.")
        X = feature_matrix[ALL_FEATURES].copy()
        probs = np.stack(
            [m.predict_proba(X)[:, 1] for m in self._fold_models], axis=0
        )
        return probs.mean(axis=0)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, output_dir: str | Path) -> dict[str, Path]:
        """
        Save the model + metadata to output_dir.

        Files created:
          - claim_model_v{MODEL_VERSION}.pkl  — all fold models + final model + calibrators
          - claim_model_metadata.json          — config, feature list, calibration & SHAP info
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        model_path = output_dir / f"claim_model_v{MODEL_VERSION}.pkl"
        meta_path = output_dir / "claim_model_metadata.json"

        # Save model bundle
        bundle = {
            "fold_models": self._fold_models,
            "final_model": getattr(self, "_final_model", None),
            "fold_infos": self._fold_infos,
            "feature_names": self._feature_names,
            "params": self.params,
            "n_folds": self.n_folds,
            "decision_threshold": self.decision_threshold,
            "calibrator": self.calibrator,
            "fold_calibrators": self.fold_calibrators,
        }
        with open(model_path, "wb") as f:
            pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Save human-readable metadata
        meta = {
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            "n_folds": self.n_folds,
            "features": ALL_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "numeric_features": NUMERIC_FEATURES,
            "lgbm_params": self.params,
            "decision_threshold": self.decision_threshold,
            "fold_summaries": [fi.summary() for fi in self._fold_infos],
            "calibration": self.calibrator.to_dict() if self.calibrator else None,
            "explainability": {
                "method": "TreeSHAP (LightGBM pred_contrib)",
                "n_features_explained": len(ALL_FEATURES),
                "base_value": getattr(self.explainer, "base_value", None) if self.explainer else None,
            },
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return {"model": model_path, "metadata": meta_path}

    @classmethod
    def load(cls, output_dir: str | Path) -> "ClaimRiskModel":
        """Load a previously saved model from output_dir."""
        output_dir = Path(output_dir)
        model_path = output_dir / f"claim_model_v{MODEL_VERSION}.pkl"

        if not model_path.exists():
            # Search for any model pkl file
            matching = list(output_dir.glob("claim_model_v*.pkl"))
            if matching:
                model_path = matching[0]
            else:
                raise FileNotFoundError(f"No claim_model pkl found in {output_dir}")

        with open(model_path, "rb") as f:
            bundle = pickle.load(f)

        instance = cls(
            params=bundle["params"],
            n_folds=bundle["n_folds"],
            decision_threshold=bundle["decision_threshold"],
        )
        instance._fold_models = bundle["fold_models"]
        instance._final_model = bundle.get("final_model")
        instance._fold_infos = bundle["fold_infos"]
        instance._feature_names = bundle["feature_names"]
        instance.calibrator = bundle.get("calibrator")
        instance.fold_calibrators = bundle.get("fold_calibrators", [])
        if instance._final_model is not None:
            instance.explainer = TreeSHAPExplainer(instance._final_model, instance._feature_names)
        instance._is_fitted = True
        return instance


# ------------------------------------------------------------------
# Target label preparation
# ------------------------------------------------------------------


def prepare_target(
    claims: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
) -> np.ndarray:
    """
    Prepare the binary target vector y from ground truth labels.
    """
    if gt_claim_labels.empty:
        return np.zeros(len(claims), dtype=np.int8)

    label_map = (
        gt_claim_labels[["claim_id", "is_suspicious"]]
        .drop_duplicates("claim_id")
        .set_index("claim_id")["is_suspicious"]
    )

    y = claims["claim_id"].map(label_map).fillna(0).astype(np.int8).values
    return y


# ------------------------------------------------------------------
# End-to-end pipeline
# ------------------------------------------------------------------


def train_and_predict(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    members: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
    output_dir: str | Path,
    n_folds: int = N_FOLDS,
    random_state: int = 42,
    params: Optional[dict[str, Any]] = None,
) -> tuple[pd.DataFrame, ClaimRiskModel, list[FoldInfo]]:
    """
    Full Phase 2 end-to-end training, calibration, and SHAP pipeline.

    Steps:
      1. Build leakage-free feature matrix
      2. Prepare binary target labels
      3. Fit provider-grouped OOF LightGBM
      4. Fit leakage-free out-of-fold isotonic calibration
      5. Train final model on full data & fit final calibrator
      6. Compute out-of-fold TreeSHAP explanations
      7. Assemble updated claim_ml output DataFrame with calibrated probabilities
         and top feature explainability
      8. Save claim_ml.parquet and model artifacts

    Returns
    -------
    claim_ml : DataFrame with calibrated predictions and SHAP explainability
    model    : fitted ClaimRiskModel (with calibrator & explainer)
    fold_infos : list of FoldInfo for audit
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Feature matrix (leakage-free)
    print("[ClaimModel] Building feature matrix...")
    feat_matrix = build_claim_feature_matrix(claims, providers, members)

    # 2. Target labels — ground truth used ONLY here
    y = prepare_target(feat_matrix, gt_claim_labels)

    # 3. Provider grouping key
    provider_ids = feat_matrix["provider_id"]

    # 4. OOF training
    print(f"[ClaimModel] Training {n_folds}-fold provider-grouped OOF LightGBM...")
    model = ClaimRiskModel(params=params, n_folds=n_folds, random_state=random_state)
    X_feat = feat_matrix[ALL_FEATURES]
    oof_probs = model.fit_oof(X_feat, y, provider_ids)

    # 5. Final model on full data (for inference)
    print("[ClaimModel] Training final model on full dataset...")
    model.train_final(X_feat, y)

    # 6. Audit fold integrity
    audit = validate_oof_integrity(model._fold_infos, feat_matrix.index, provider_ids)
    for summary in audit["fold_summaries"]:
        print(f"  {summary}")

    # 7. Assign OOF fold membership per claim
    fold_assignments = np.zeros(len(feat_matrix), dtype=int)
    from vigilx.ml.oof import provider_grouped_kfold
    for train_idx, val_idx, fi in provider_grouped_kfold(
        X_feat, y, provider_ids, n_splits=n_folds, random_state=random_state
    ):
        fold_assignments[val_idx] = fi.fold

    # 8. Leakage-free OOF Calibration
    print("[ClaimModel] Fitting provider-grouped OOF isotonic calibration...")
    calibrated_probs, fold_calibrators = calibrate_oof(
        oof_probs=oof_probs,
        y=y,
        fold_assignments=fold_assignments,
        n_folds=n_folds,
    )
    model.fold_calibrators = fold_calibrators
    model.oof_calibrated_probs = calibrated_probs

    # Fit final calibrator on all OOF predictions (for new claims at inference)
    final_calibrator = fit_final_calibrator(oof_probs, y)
    model.calibrator = final_calibrator

    # 9. Compute OOF TreeSHAP Explanations
    print("[ClaimModel] Computing OOF TreeSHAP explanations...")
    oof_shap, base_values = compute_oof_shap(
        fold_models=model._fold_models,
        X=X_feat,
        fold_assignments=fold_assignments,
        feature_names=ALL_FEATURES,
    )
    model.oof_shap_values = oof_shap
    top_features_df = batch_extract_top_features(oof_shap, ALL_FEATURES, top_k=3)

    # 10. Build updated output schema
    now_utc = datetime.now(tz=timezone.utc).isoformat()
    claim_ml = pd.DataFrame({
        "claim_id": feat_matrix["claim_id"].values,
        "provider_id": feat_matrix["provider_id"].values,
        "ml_probability": oof_probs.astype(np.float32),
        "calibrated_probability": calibrated_probs.astype(np.float32),
        "ml_prediction": (calibrated_probs >= model.decision_threshold).astype(np.int8),
        "oof_fold": fold_assignments.astype(np.int8),
        "top_features": top_features_df["top_features"].values,
        "top_feature_1": top_features_df["top_feature_1"].values,
        "top_feature_1_shap": top_features_df["top_feature_1_shap"].values,
        "top_feature_2": top_features_df["top_feature_2"].values,
        "top_feature_2_shap": top_features_df["top_feature_2_shap"].values,
        "top_feature_3": top_features_df["top_feature_3"].values,
        "top_feature_3_shap": top_features_df["top_feature_3_shap"].values,
        "ml_risk_score": oof_probs.astype(np.float32),   # alias for backwards compatibility
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "prediction_timestamp": now_utc,
    })

    # 11. Save output
    claim_ml_path = output_dir / "claim_ml.parquet"
    claim_ml.to_parquet(claim_ml_path, index=False)
    print(f"[ClaimModel] Saved claim_ml.parquet → {claim_ml_path}")

    # 12. Save model artifacts
    artifact_paths = model.save(output_dir)
    print(f"[ClaimModel] Saved model → {artifact_paths['model']}")

    return claim_ml, model, model._fold_infos
