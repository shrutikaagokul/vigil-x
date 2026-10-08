"""
TreeSHAP explainability for Vigil-X LightGBM claim risk model.

Exposes claim-level feature attributions using LightGBM's fast, native C++
TreeSHAP implementation (pred_contrib=True), avoiding heavy external dependencies
while guaranteeing exact Shapley values.

CORE PRINCIPLES:
  1. Additive Efficiency: Sum of SHAP values + base value strictly equals
     the model's raw log-odds margin score.
  2. Provider Non-Leakage in OOF Explanations: OOF claims are explained using
     the fold model that never saw that provider during training.
  3. Actionable SIU Summaries: Ranks top risk-driving features with direction
     (+ / -) and exact contribution for investigator inspection.
  4. Lean Footprint: Extracts structured top-feature explanations without
     generating bloated multi-gigabyte disk artifacts.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import numpy as np
import pandas as pd


class TreeSHAPExplainer:
    """
    Fast TreeSHAP explainer for LightGBM models.

    Parameters
    ----------
    model : object
        Fitted LightGBM model or booster instance.
    feature_names : list[str]
        List of feature column names corresponding to the model inputs.
    """

    def __init__(self, model: Any, feature_names: list[str]) -> None:
        self.model = model
        self.feature_names = list(feature_names)
        self.booster = getattr(model, "booster_", model)
        self._base_value: Optional[float] = None

    @property
    def base_value(self) -> Optional[float]:
        """Expected value / prior bias in margin (log-odds) space.

        Returns None if base value has not yet been computed via compute_shap_values().
        """
        return self._base_value

    def compute_shap_values(self, X: pd.DataFrame) -> tuple[np.ndarray, float]:
        """
        Compute TreeSHAP attributions for feature matrix X.

        Parameters
        ----------
        X : DataFrame
            Feature matrix with columns matching self.feature_names.

        Returns
        -------
        shap_values : ndarray of shape (n_samples, n_features)
            SHAP values in margin (log-odds) space.
        base_value : float
            Expected baseline margin score.
        """
        X_df = X[self.feature_names].copy()
        contribs = self.booster.predict(X_df, pred_contrib=True)
        shap_values = contribs[:, :-1]
        base_val = float(contribs[0, -1])
        self._base_value = base_val
        return shap_values, base_val

    def explain_claim(
        self,
        claim_id: str,
        feature_vector: pd.DataFrame | pd.Series | np.ndarray,
        calibrated_probability: Optional[float] = None,
        top_k: int = 4,
    ) -> dict[str, Any]:
        """
        Produce a structured explanation for a single claim.
        """
        if isinstance(feature_vector, pd.Series):
            df = pd.DataFrame([feature_vector])[self.feature_names]
        elif isinstance(feature_vector, pd.DataFrame):
            df = feature_vector[self.feature_names].iloc[:1]
        else:
            df = pd.DataFrame(np.asarray(feature_vector).reshape(1, -1), columns=self.feature_names)

        shap_vals, base_val = self.compute_shap_values(df)
        shap_row = shap_vals[0]

        top_features = extract_top_features_single(
            shap_row, self.feature_names, top_k=top_k
        )

        formatted_text = format_claim_explanation(
            claim_id=claim_id,
            calibrated_probability=calibrated_probability,
            top_features=top_features,
        )

        return {
            "claim_id": claim_id,
            "calibrated_probability": calibrated_probability,
            "base_value": round(base_val, 4),
            "top_features": top_features,
            "formatted_text": formatted_text,
        }


def compute_oof_shap(
    fold_models: list[Any],
    X: pd.DataFrame,
    fold_assignments: np.ndarray,
    feature_names: list[str],
) -> tuple[np.ndarray, dict[int, float]]:
    """
    Compute out-of-fold TreeSHAP attributions using fold models.

    For each fold k:
      - Validates fold k claims using fold model k (trained without fold k providers).
      - Collects SHAP values and base values.

    Returns
    -------
    oof_shap : ndarray of shape (n_claims, n_features)
    base_values : dict of {fold: base_value}
    """
    n_claims = len(X)
    n_features = len(feature_names)
    oof_shap = np.zeros((n_claims, n_features), dtype=np.float32)
    base_values: dict[int, float] = {}

    X_feats = X[feature_names].copy()
    unique_folds = sorted(int(f) for f in np.unique(fold_assignments) if f > 0)

    for fold in unique_folds:
        val_mask = fold_assignments == fold
        if not np.any(val_mask):
            continue

        model = fold_models[fold - 1]
        booster = getattr(model, "booster_", model)

        X_val = X_feats.iloc[val_mask]
        contribs = booster.predict(X_val, pred_contrib=True)
        oof_shap[val_mask] = contribs[:, :-1].astype(np.float32)
        base_values[fold] = float(contribs[0, -1])

    return oof_shap, base_values


def extract_top_features_single(
    shap_vector: np.ndarray,
    feature_names: list[str],
    top_k: int = 4,
    mode: str = "risk_drivers",
) -> dict[str, float]:
    """
    Extract top contributing features for a single sample.

    Parameters
    ----------
    shap_vector : ndarray of shape (n_features,)
    feature_names : list of feature names
    top_k : number of top features to return
    mode : 'risk_drivers' (positive first) or 'absolute' (by abs magnitude)

    Returns
    -------
    dict of {feature_name: signed_shap_value}
    """
    shap_vector = np.asarray(shap_vector, dtype=float)
    feat_names = list(feature_names)

    if mode == "risk_drivers":
        # Prioritize positive contributors (risk drivers), sorted descending
        pos_indices = [i for i, v in enumerate(shap_vector) if v > 0]
        pos_indices.sort(key=lambda i: shap_vector[i], reverse=True)

        if len(pos_indices) >= top_k:
            selected_indices = pos_indices[:top_k]
        else:
            # Fill remaining slots with largest absolute negative contributors
            neg_indices = [i for i in range(len(shap_vector)) if i not in pos_indices]
            neg_indices.sort(key=lambda i: abs(shap_vector[i]), reverse=True)
            selected_indices = pos_indices + neg_indices[: top_k - len(pos_indices)]
    else:
        # Sort strictly by absolute magnitude
        selected_indices = sorted(
            range(len(shap_vector)), key=lambda i: abs(shap_vector[i]), reverse=True
        )[:top_k]

    return {
        feat_names[idx]: round(float(shap_vector[idx]), 4)
        for idx in selected_indices
    }


def format_claim_explanation(
    claim_id: str,
    calibrated_probability: Optional[float],
    top_features: dict[str, float],
) -> str:
    """
    Format a claim explanation matching the Vigil-X Phase 2 human-readable contract.

    Example output:
      claim_id: C1042
      calibrated_probability: 0.87

      top_features:
        procedure_mix: +0.21
        claim_amount: +0.16
        utilization_30d: +0.12
        em_level: +0.09
    """
    lines = [f"claim_id: {claim_id}"]
    if calibrated_probability is not None:
        lines.append(f"calibrated_probability: {calibrated_probability:.2f}")
    lines.append("")
    lines.append("top_features:")
    for feat, val in top_features.items():
        sign = "+" if val >= 0 else ""
        lines.append(f"  {feat}: {sign}{val:.2f}")

    return "\n".join(lines)


def batch_extract_top_features(
    shap_matrix: np.ndarray,
    feature_names: list[str],
    top_k: int = 3,
    n_top: Optional[int] = None,
) -> pd.DataFrame:
    """
    Efficiently extract top-K feature explanations for an entire dataset.

    Returns a DataFrame with columns:
      - top_features: JSON-encoded dictionary of top features
      - top_feature_1: Name of the #1 contributing feature
      - top_feature_1_shap: SHAP attribution of the #1 feature
      - top_feature_2: Name of the #2 contributing feature
      - top_feature_2_shap: SHAP attribution of the #2 feature
      - top_feature_3: Name of the #3 contributing feature
      - top_feature_3_shap: SHAP attribution of the #3 feature
    """
    if n_top is not None:
        top_k = n_top

    n_samples = len(shap_matrix)
    feat_names = np.array(feature_names)

    # Sort descending by contribution (positive first)
    top_indices = np.argsort(-shap_matrix, axis=1)[:, :top_k]

    top_json: list[str] = []
    f1_names, f1_vals = [], []
    f2_names, f2_vals = [], []
    f3_names, f3_vals = [], []

    for i in range(n_samples):
        indices = top_indices[i]
        d = {feat_names[idx]: round(float(shap_matrix[i, idx]), 4) for idx in indices}
        top_json.append(json.dumps(d))

        f1_names.append(str(feat_names[indices[0]]))
        f1_vals.append(float(np.round(shap_matrix[i, indices[0]], 4)))

        if top_k > 1:
            f2_names.append(str(feat_names[indices[1]]))
            f2_vals.append(float(np.round(shap_matrix[i, indices[1]], 4)))
        else:
            f2_names.append(None)
            f2_vals.append(0.0)

        if top_k > 2:
            f3_names.append(str(feat_names[indices[2]]))
            f3_vals.append(float(np.round(shap_matrix[i, indices[2]], 4)))
        else:
            f3_names.append(None)
            f3_vals.append(0.0)

    return pd.DataFrame({
        "top_features": top_json,
        "top_feature_1": f1_names,
        "top_feature_1_shap": np.array(f1_vals, dtype=np.float32),
        "top_feature_2": f2_names,
        "top_feature_2_shap": np.array(f2_vals, dtype=np.float32),
        "top_feature_3": f3_names,
        "top_feature_3_shap": np.array(f3_vals, dtype=np.float32),
    })
