"""
Isolation Forest provider anomaly detection for Vigil-X.

Detects providers whose behavioral patterns are statistically unusual
compared with their peers, using unsupervised anomaly detection.

CONCEPT:
  LightGBM (claim_model):   "Is this individual claim suspicious?"
  Isolation Forest (here):  "Does this provider behave unusually?"

DESIGN PRINCIPLES:
  1. Fully unsupervised — ground truth labels are NEVER used as features.
  2. Features are derived exclusively from observed claim behavior.
  3. Deterministic: fixed random_state=42 for reproducibility.
  4. Contamination estimated as proportion of known FWA providers
     (if available), otherwise defaults to 0.05 (5%).
  5. Evaluation uses planted FWA scenarios for precision@K / recall@K.
  6. Output score is Isolation Forest anomaly score (higher = more anomalous).
     It is NOT a fraud probability.

OUTPUT SCHEMA:
  provider_id         str
  anomaly_score       float  — raw IF decision function (higher = more anomalous)
  anomaly_percentile  float  — percentile rank [0, 100]
  anomaly_flag        int    — 1 if above contamination threshold, else 0
  model_version       str
  feature_version     str
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
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from vigilx.ml.provider_features_ml import (
    PROVIDER_ANOMALY_FEATURE_VERSION,
    PROVIDER_ANOMALY_FEATURES,
    build_provider_behavioral_features,
)
from vigilx.ml.metrics_utils import precision_at_k, recall_at_k

ANOMALY_MODEL_VERSION = "1.0.0"


class ProviderAnomalyDetector:
    """
    Isolation Forest-based provider anomaly detector.

    Parameters
    ----------
    n_estimators : int, default 200
        Number of Isolation Forest trees.
    contamination : float or 'auto', default 0.05
        Expected proportion of anomalous providers.
    random_state : int, default 42
        Reproducibility seed.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        contamination: float = 0.05,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

        self._iso_forest: Optional[IsolationForest] = None
        self._scaler: Optional[RobustScaler] = None
        self._feature_names: list[str] = []
        self._is_fitted: bool = False
        self._threshold: Optional[float] = None

    def fit(self, X: pd.DataFrame) -> "ProviderAnomalyDetector":
        """
        Fit Isolation Forest on provider behavioral feature matrix.

        Parameters
        ----------
        X : DataFrame with columns matching PROVIDER_ANOMALY_FEATURES
        """
        self._feature_names = [f for f in PROVIDER_ANOMALY_FEATURES if f in X.columns]
        X_fit = X[self._feature_names].copy()

        # RobustScaler is insensitive to outliers — appropriate for FWA data
        self._scaler = RobustScaler()
        X_scaled = self._scaler.fit_transform(X_fit)

        self._iso_forest = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._iso_forest.fit(X_scaled)

        self._is_fitted = True
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        """
        Compute anomaly scores.

        IsolationForest.decision_function returns:
          - Negative scores → more anomalous
          - Positive scores → more normal

        We NEGATE and shift to produce:
          - Higher score → more anomalous (more intuitive for ranking)
        """
        self._check_fitted()
        X_score = X[self._feature_names].copy()
        X_scaled = self._scaler.transform(X_score)
        raw = self._iso_forest.decision_function(X_scaled)
        # Negate: higher score = more anomalous
        return -raw.astype(np.float32)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return binary anomaly flags (1 = anomalous, 0 = normal).
        IsolationForest.predict returns +1 (normal) or -1 (anomaly).
        We convert to 0/1.
        """
        self._check_fitted()
        X_score = X[self._feature_names].copy()
        X_scaled = self._scaler.transform(X_score)
        raw = self._iso_forest.predict(X_scaled)
        return ((raw == -1).astype(np.int8))

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError("Call fit() before score() or predict().")

    def save(self, output_dir: str | Path) -> dict[str, Path]:
        """Save model bundle and metadata."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        model_path = output_dir / f"provider_anomaly_v{ANOMALY_MODEL_VERSION}.pkl"
        meta_path = output_dir / "provider_anomaly_metadata.json"

        bundle = {
            "iso_forest": self._iso_forest,
            "scaler": self._scaler,
            "feature_names": self._feature_names,
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
        }
        with open(model_path, "wb") as f:
            pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

        meta = {
            "model_version": ANOMALY_MODEL_VERSION,
            "feature_version": PROVIDER_ANOMALY_FEATURE_VERSION,
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "feature_names": self._feature_names,
            "n_features": len(self._feature_names),
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return {"model": model_path, "metadata": meta_path}

    @classmethod
    def load(cls, output_dir: str | Path) -> "ProviderAnomalyDetector":
        output_dir = Path(output_dir)
        matches = list(output_dir.glob("provider_anomaly_v*.pkl"))
        if not matches:
            raise FileNotFoundError(f"No provider_anomaly pkl found in {output_dir}")
        with open(matches[0], "rb") as f:
            bundle = pickle.load(f)
        instance = cls(
            n_estimators=bundle["n_estimators"],
            contamination=bundle["contamination"],
            random_state=bundle["random_state"],
        )
        instance._iso_forest = bundle["iso_forest"]
        instance._scaler = bundle["scaler"]
        instance._feature_names = bundle["feature_names"]
        instance._is_fitted = True
        return instance


def fit_provider_anomaly(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    output_dir: str | Path,
    contamination: float = 0.05,
    random_state: int = 42,
    n_estimators: int = 200,
    snapshot_date: Optional[str] = None,
) -> tuple[pd.DataFrame, ProviderAnomalyDetector]:
    """
    Full Isolation Forest pipeline for provider anomaly detection.

    Steps:
      1. Build provider behavioral features from claims
      2. Fit Isolation Forest (unsupervised, no ground truth used)
      3. Compute anomaly scores and flags for all providers
      4. Save output parquet and model artifacts

    Parameters
    ----------
    claims : raw claims DataFrame
    providers : provider metadata DataFrame
    output_dir : directory to save outputs
    contamination : expected anomalous fraction (default 0.05 = 5%)
    random_state : reproducibility seed
    n_estimators : Isolation Forest trees
    snapshot_date : optional cutoff date for temporal correctness

    Returns
    -------
    provider_anomaly : DataFrame with provider_id, anomaly_score, anomaly_flag
    model : fitted ProviderAnomalyDetector
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[AnomalyDetector] Building provider behavioral features...")
    feat = build_provider_behavioral_features(claims, providers, snapshot_date=snapshot_date)

    if len(feat) == 0:
        raise ValueError("No provider features computed — claims may be empty.")

    print(f"[AnomalyDetector] Fitting Isolation Forest on {len(feat)} providers, "
          f"{len(PROVIDER_ANOMALY_FEATURES)} features, contamination={contamination}...")

    detector = ProviderAnomalyDetector(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    detector.fit(feat)

    anomaly_scores = detector.score(feat)
    anomaly_flags = detector.predict(feat)

    # Percentile rank (higher = more anomalous)
    from scipy.stats import rankdata
    anomaly_percentile = rankdata(anomaly_scores, method="average") / len(anomaly_scores) * 100

    now_utc = datetime.now(tz=timezone.utc).isoformat()
    provider_anomaly = pd.DataFrame({
        "provider_id": feat["provider_id"].values,
        "anomaly_score": anomaly_scores,
        "anomaly_percentile": anomaly_percentile.astype(np.float32),
        "anomaly_flag": anomaly_flags,
        "model_version": ANOMALY_MODEL_VERSION,
        "feature_version": PROVIDER_ANOMALY_FEATURE_VERSION,
        "scored_at": now_utc,
    })

    # Sort by anomaly_score descending (most anomalous first)
    provider_anomaly = provider_anomaly.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    # Save output
    out_path = output_dir / "provider_anomaly.parquet"
    provider_anomaly.to_parquet(out_path, index=False)
    print(f"[AnomalyDetector] Saved provider_anomaly.parquet → {out_path}")
    print(f"[AnomalyDetector] Flagged anomalous providers: {int(anomaly_flags.sum())} / {len(feat)}")

    # Save model artifacts
    detector.save(output_dir)

    return provider_anomaly, detector


def evaluate_provider_anomaly(
    provider_anomaly: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
    ks: Optional[list[int]] = None,
) -> dict[str, Any]:
    """
    Evaluate Isolation Forest against planted FWA providers.

    IMPORTANT: This is unsupervised anomaly detection, not supervised classification.
    We evaluate against known planted scenarios to understand signal quality.
    The model was NOT trained on these labels.

    Parameters
    ----------
    provider_anomaly : output from fit_provider_anomaly()
    gt_entity_labels : ground truth from synthetic data generator
    ks : K values for precision@K and recall@K

    Returns
    -------
    dict with precision@K, recall@K, anomaly overlap, and rank metrics
    """
    if ks is None:
        ks = [5, 10, 25, 50]

    # Extract suspicious providers from GT
    suspicious_providers = set(
        gt_entity_labels[
            (gt_entity_labels["entity_type"] == "provider") &
            (gt_entity_labels["is_suspicious"] == 1)
        ]["entity_id"]
    )
    n_suspicious = len(suspicious_providers)

    if n_suspicious == 0:
        return {"warning": "No suspicious providers in ground truth."}

    # Sort by anomaly_score descending (already sorted, but ensure)
    ranked = provider_anomaly.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    y_true = ranked["provider_id"].isin(suspicious_providers).astype(int).values
    y_score = ranked["anomaly_score"].values.astype(float)

    # Build metrics
    from sklearn.metrics import roc_auc_score
    from vigilx.ml.metrics_utils import compute_average_precision

    n_flagged = int((ranked["anomaly_flag"] == 1).sum())
    flagged_providers = set(ranked[ranked["anomaly_flag"] == 1]["provider_id"])
    tp_flagged = len(flagged_providers & suspicious_providers)
    fp_flagged = n_flagged - tp_flagged

    metrics: dict[str, Any] = {
        "n_providers": len(ranked),
        "n_suspicious_gt": n_suspicious,
        "n_flagged": n_flagged,
        "n_true_positive_flagged": tp_flagged,
        "n_false_positive_flagged": fp_flagged,
        "flag_precision": round(tp_flagged / n_flagged, 4) if n_flagged > 0 else 0.0,
        "flag_recall": round(tp_flagged / n_suspicious, 4) if n_suspicious > 0 else 0.0,
    }

    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
        metrics["pr_auc"] = round(compute_average_precision(y_true, y_score), 4)
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None

    for k in ks:
        metrics[f"precision_at_{k}"] = round(precision_at_k(y_true, y_score, k), 4)
        metrics[f"recall_at_{k}"] = round(recall_at_k(y_true, y_score, k), 4)

    # Rank-lift vs random baseline
    random_p_at_k = n_suspicious / len(ranked)
    for k in ks:
        ml_p = metrics.get(f"precision_at_{k}", 0.0)
        lift = ml_p / random_p_at_k if random_p_at_k > 0 else 0.0
        metrics[f"rank_lift_at_{k}"] = round(lift, 2)

    return metrics


# Pipeline alias
train_and_detect = fit_provider_anomaly

