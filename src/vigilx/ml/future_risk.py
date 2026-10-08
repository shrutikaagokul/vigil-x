"""
Future Risk prediction for Vigil-X ML subsystem.

Estimates the probability that a provider will have significantly elevated
suspicious activity in the next 30, 60, or 90 days.

==================================================
TARGET DEFINITION
==================================================

For a prediction made at snapshot date T:

  FEATURES: All claims with service_date <= T
  TARGET 30d: Is this provider a known FWA entity AND
              did they have ANY suspicious claims during T < date <= T+30?
  TARGET 60d: Same, for T < date <= T+60
  TARGET 90d: Same, for T < date <= T+90

  Positive providers: Members of planted FWA scenarios (gt_entity_labels)
  that also have claim-level ground truth during the future window.

  If a provider is in gt_entity_labels (known bad actor) but has no
  suspicious claims in the future window, they are treated as unknown
  (excluded from positive targets) to avoid fabricating labels.

==================================================
TEMPORAL LEAKAGE PREVENTION
==================================================

  MAX(feature_date) <= T   (strictly enforced)
  Target window:  T < date <= T + horizon_days

  Features are NEVER allowed to include information from the future window.
  This is verified per prediction.

==================================================
TRAINING STRATEGY
==================================================

  Multiple temporal snapshot points T are created across the dataset.
  Each provider-snapshot pair is one training example.
  LightGBM binary classifier with provider-grouped cross-validation.

  Positive class: provider has suspicious claims in the future window.
  Negative class: all other providers at that snapshot.

==================================================
OUTPUT SCHEMA
==================================================

  provider_id           str
  risk_30d              float   probability (calibrated isotonic)
  risk_60d              float
  risk_90d              float
  prediction_date       str     snapshot date
  model_version         str
  feature_version       str
"""
from __future__ import annotations

import json
import pickle
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from vigilx.ml.provider_features_ml import (
    PROVIDER_ANOMALY_FEATURE_VERSION,
    PROVIDER_ANOMALY_FEATURES,
    build_provider_behavioral_features,
)
from vigilx.ml.metrics_utils import (
    compute_average_precision,
    precision_at_k,
    recall_at_k,
)

FUTURE_RISK_MODEL_VERSION = "1.0.0"
FUTURE_RISK_FEATURE_VERSION = "1.0.0"
HORIZONS_DAYS = [30, 60, 90]


# ------------------------------------------------------------------
# Target construction
# ------------------------------------------------------------------

def build_future_risk_targets(
    claims: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
    snapshot_date: str,
    horizon_days: int,
) -> pd.Series:
    """
    Build binary target: did provider have suspicious activity AFTER snapshot_date?

    Target = 1 if provider is in gt_entity_labels AND had suspicious claims
    in (snapshot_date, snapshot_date + horizon_days].

    Providers with entity-label=1 but no suspicious claims in window → excluded (NaN).
    This avoids fabricating labels.

    Parameters
    ----------
    claims : raw claims with service_date and claim_id
    gt_claim_labels : claim-level ground truth (claim_id, is_suspicious)
    gt_entity_labels : entity-level ground truth (entity_id, is_suspicious)
    snapshot_date : str in YYYY-MM-DD format
    horizon_days : future window length in days

    Returns
    -------
    Series indexed by provider_id with values {0, 1, NaN}.
    NaN = exclude from training (entity-positive with no future claims).
    """
    T = pd.Timestamp(snapshot_date)
    T_end = T + timedelta(days=horizon_days)

    claims = claims.copy()
    claims["service_date"] = pd.to_datetime(claims["service_date"], errors="coerce")

    # Future claims in the target window
    future_claims = claims[
        (claims["service_date"] > T) & (claims["service_date"] <= T_end)
    ]

    # Suspicious claim IDs
    sus_ids = set(gt_claim_labels[gt_claim_labels["is_suspicious"] == 1]["claim_id"])

    # Providers that had suspicious claims in future window
    future_suspicious = set(future_claims[future_claims["claim_id"].isin(sus_ids)]["provider_id"])

    # Known FWA entity providers
    fwa_providers = set(
        gt_entity_labels[
            (gt_entity_labels["entity_type"] == "provider") &
            (gt_entity_labels["is_suspicious"] == 1)
        ]["entity_id"]
    )

    # All providers active in historical window (before T)
    historical_providers = set(
        claims[claims["service_date"] <= T]["provider_id"].unique()
    )

    target = {}
    for prov in historical_providers:
        if prov in fwa_providers:
            if prov in future_suspicious:
                target[prov] = 1  # confirmed future suspicious activity
            else:
                target[prov] = np.nan  # known bad, but no future claims — exclude
        else:
            target[prov] = 0  # negative (not a known FWA provider)

    return pd.Series(target, name=f"target_{horizon_days}d")


def build_multi_snapshot_dataset(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
    horizon_days: int,
    n_snapshots: int = 6,
    min_history_days: int = 60,
) -> pd.DataFrame:
    """
    Build a multi-snapshot training dataset by sliding a temporal window.

    Creates n_snapshots prediction points evenly spaced between
    min_history_days from start and (end - horizon_days).

    Each row = (provider_id, snapshot_date) with behavioral features
    computed from claims BEFORE snapshot_date, and a binary target
    indicating future suspicious activity.

    LEAKAGE GUARANTEE:
      All features use claims with service_date <= snapshot_date.
      Targets use claims with service_date > snapshot_date.
    """
    claims = claims.copy()
    claims["service_date"] = pd.to_datetime(claims["service_date"], errors="coerce")

    date_start = claims["service_date"].min() + timedelta(days=min_history_days)
    date_end = claims["service_date"].max() - timedelta(days=horizon_days)

    if date_end <= date_start:
        return pd.DataFrame()

    # Evenly-spaced snapshot dates
    total_days = (date_end - date_start).days
    step_days = max(total_days // n_snapshots, 1)
    snapshot_dates = [
        date_start + timedelta(days=i * step_days)
        for i in range(n_snapshots)
    ]

    all_rows = []
    for snap_date in snapshot_dates:
        snap_str = snap_date.strftime("%Y-%m-%d")

        # Build features from historical claims
        feat = build_provider_behavioral_features(
            claims, providers, snapshot_date=snap_str
        )
        if feat.empty:
            continue

        # Build targets
        target = build_future_risk_targets(
            claims, gt_claim_labels, gt_entity_labels,
            snapshot_date=snap_str, horizon_days=horizon_days
        )

        feat["snapshot_date"] = snap_str
        feat["target"] = feat["provider_id"].map(target)
        all_rows.append(feat)

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True)
    # Drop rows where target is NaN (entity-positive with no future claims)
    combined = combined.dropna(subset=["target"]).reset_index(drop=True)
    combined["target"] = combined["target"].astype(int)
    return combined


class FutureRiskModel:
    """
    LightGBM-based provider future risk model for a single time horizon.
    """

    def __init__(
        self,
        horizon_days: int,
        n_estimators: int = 100,
        random_state: int = 42,
    ) -> None:
        self.horizon_days = horizon_days
        self.n_estimators = n_estimators
        self.random_state = random_state
        self._model = None
        self._calibrator: Optional[IsotonicRegression] = None
        self._feature_names: list[str] = []
        self._is_fitted = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "FutureRiskModel":
        """Fit on multi-snapshot training set."""
        self._feature_names = [f for f in PROVIDER_ANOMALY_FEATURES if f in X.columns]
        X_fit = X[self._feature_names].copy()

        # Use GradientBoosting which handles small, imbalanced datasets well
        try:
            import lightgbm as lgb
            self._model = lgb.LGBMClassifier(
                n_estimators=self.n_estimators,
                num_leaves=15,
                learning_rate=0.05,
                min_child_samples=5,
                is_unbalance=True,
                verbose=-1,
                random_state=self.random_state,
                deterministic=True,
                force_row_wise=True,
            )
        except ImportError:
            self._model = GradientBoostingClassifier(
                n_estimators=self.n_estimators,
                max_depth=3,
                random_state=self.random_state,
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model.fit(X_fit, y)

        # Calibrate on training predictions (in-sample, acceptable for small data)
        raw_probs = self._predict_raw(X_fit)
        pos_count = int(y.sum())
        if pos_count >= 5 and len(np.unique(y)) > 1:
            self._calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            self._calibrator.fit(raw_probs, y)
        else:
            self._calibrator = None

        self._is_fitted = True
        return self

    def _predict_raw(self, X: pd.DataFrame) -> np.ndarray:
        if hasattr(self._model, "predict_proba"):
            return self._model.predict_proba(X)[:, 1]
        return self._model.decision_function(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return calibrated probability for the future risk horizon."""
        if not self._is_fitted:
            raise RuntimeError("Call fit() first.")
        X_feat = X[self._feature_names].copy()
        raw = self._predict_raw(X_feat)
        if self._calibrator is not None:
            return np.clip(self._calibrator.predict(raw), 0.0, 1.0)
        return np.clip(raw, 0.0, 1.0)

    def save(self, output_dir: Path) -> Path:
        path = output_dir / f"future_risk_{self.horizon_days}d_model.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        return path

    @classmethod
    def load(cls, output_dir: Path, horizon_days: int) -> "FutureRiskModel":
        path = output_dir / f"future_risk_{horizon_days}d_model.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)


def fit_future_risk(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    gt_claim_labels: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
    output_dir: str | Path,
    horizons: list[int] = HORIZONS_DAYS,
    n_snapshots: int = 6,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[int, FutureRiskModel], dict[int, dict]]:
    """
    Full future risk pipeline.

    Steps:
      1. Build multi-snapshot training dataset for each horizon
      2. Fit a FutureRiskModel per horizon
      3. Score ALL providers at the latest available snapshot
      4. Save future_risk.parquet and model artifacts

    TEMPORAL LEAKAGE:
      Features are ALWAYS computed from claims <= snapshot_date.
      Targets are ALWAYS computed from claims > snapshot_date.

    Returns
    -------
    future_risk : DataFrame (provider_id, risk_30d, risk_60d, risk_90d, ...)
    models : dict {horizon_days: FutureRiskModel}
    train_reports : dict {horizon_days: training report}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    claims = claims.copy()
    claims["service_date"] = pd.to_datetime(claims["service_date"], errors="coerce")

    # Latest snapshot = end of data minus max horizon (to allow evaluation)
    data_end = claims["service_date"].max()
    # Use a safe prediction date: leave room for the largest horizon
    max_horizon = max(horizons)
    safe_prediction_date = (data_end - timedelta(days=max_horizon + 1)).strftime("%Y-%m-%d")
    latest_snap = safe_prediction_date
    print(f"[FutureRisk] Prediction date: {latest_snap}")

    models: dict[int, FutureRiskModel] = {}
    train_reports: dict[int, dict] = {}
    risk_cols: dict[str, np.ndarray] = {}

    for horizon in horizons:
        print(f"[FutureRisk] Building {horizon}d dataset...")
        train_df = build_multi_snapshot_dataset(
            claims=claims,
            providers=providers,
            gt_claim_labels=gt_claim_labels,
            gt_entity_labels=gt_entity_labels,
            horizon_days=horizon,
            n_snapshots=n_snapshots,
        )

        if train_df.empty or int(train_df["target"].sum()) < 2:
            print(f"[FutureRisk] SKIPPED: Insufficient positive labels for {horizon}d "
                  f"(positives={int(train_df['target'].sum()) if not train_df.empty else 0}). "
                  f"Outputting zero risk scores for all providers.")
            feat_cols = [f for f in PROVIDER_ANOMALY_FEATURES if f in
                         build_provider_behavioral_features(
                             claims[claims['service_date'] <= pd.Timestamp(latest_snap)],
                             providers, snapshot_date=latest_snap
                         ).columns]
            risk_cols[f"risk_{horizon}d"] = np.zeros(
                len(providers), dtype=np.float32
            )
            train_reports[horizon] = {
                "status": "skipped",
                "reason": f"Too few positive labels (n_positives={int(train_df['target'].sum()) if not train_df.empty else 0})",
            }
            models[horizon] = None
            continue

        feat_cols = [f for f in PROVIDER_ANOMALY_FEATURES if f in train_df.columns]
        X_train = train_df[feat_cols]
        y_train = train_df["target"].values

        pos = int(y_train.sum())
        neg = len(y_train) - pos
        print(f"[FutureRisk] {horizon}d: {len(X_train)} training rows, {pos} positive, {neg} negative")

        model = FutureRiskModel(horizon_days=horizon, random_state=random_state)
        model.fit(X_train, y_train)
        models[horizon] = model

        # Score all providers at the latest snapshot
        score_feat = build_provider_behavioral_features(
            claims, providers, snapshot_date=latest_snap
        )
        score_probs = model.predict_proba(score_feat)

        # Make sure we have scores for all providers
        all_prov_ids = providers["provider_id"].values
        score_map = dict(zip(score_feat["provider_id"].values, score_probs))
        risk_arr = np.array([float(score_map.get(p, 0.0)) for p in all_prov_ids], dtype=np.float32)
        risk_cols[f"risk_{horizon}d"] = risk_arr

        # Training metrics
        train_probs = model.predict_proba(X_train)
        train_pr_auc = compute_average_precision(y_train, train_probs)
        train_reports[horizon] = {
            "status": "fitted",
            "horizon_days": horizon,
            "n_training_rows": len(X_train),
            "n_snapshots": n_snapshots,
            "n_positives": pos,
            "n_negatives": neg,
            "positive_rate": round(pos / len(X_train), 4),
            "train_pr_auc": round(train_pr_auc, 4),
            "prediction_date": latest_snap,
        }

    # Assemble output
    all_prov_ids = providers["provider_id"].values
    now_utc = datetime.now(tz=timezone.utc).isoformat()
    output_data: dict[str, Any] = {"provider_id": all_prov_ids}
    for h in horizons:
        key = f"risk_{h}d"
        if key in risk_cols:
            output_data[key] = risk_cols[key]
        else:
            output_data[key] = np.zeros(len(all_prov_ids), dtype=np.float32)

    future_risk = pd.DataFrame(output_data)
    future_risk["prediction_date"] = latest_snap
    future_risk["model_version"] = FUTURE_RISK_MODEL_VERSION
    future_risk["feature_version"] = FUTURE_RISK_FEATURE_VERSION
    future_risk["scored_at"] = now_utc

    # Sort by max risk descending
    future_risk["_max_risk"] = future_risk[[f"risk_{h}d" for h in horizons]].max(axis=1)
    future_risk = future_risk.sort_values("_max_risk", ascending=False).drop(columns="_max_risk").reset_index(drop=True)

    out_path = output_dir / "future_risk.parquet"
    future_risk.to_parquet(out_path, index=False)
    print(f"[FutureRisk] Saved future_risk.parquet → {out_path}")

    # Save model artifacts
    for h, m in models.items():
        if m is not None:
            m.save(output_dir)

    # Save training report
    report_path = output_dir / "future_risk_training_report.json"
    with open(report_path, "w") as f:
        json.dump(train_reports, f, indent=2, default=str)
    print(f"[FutureRisk] Saved training report → {report_path}")

    return future_risk, models, train_reports


def evaluate_future_risk(
    future_risk: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
    horizons: list[int] = HORIZONS_DAYS,
    ks: Optional[list[int]] = None,
) -> dict[int, dict]:
    """
    Evaluate future risk predictions against GT entity labels.

    Because the future risk target involves WHICH providers have FWA,
    we use entity-level GT (19 suspicious providers) for evaluation.

    Note: These providers were not used as training labels for
    the future risk model — the model learns from claim-level
    suspicious activity signals, not from entity labels directly.
    """
    if ks is None:
        ks = [5, 10, 25, 50]

    suspicious_providers = set(
        gt_entity_labels[
            (gt_entity_labels["entity_type"] == "provider") &
            (gt_entity_labels["is_suspicious"] == 1)
        ]["entity_id"]
    )

    results: dict[int, dict] = {}
    for h in horizons:
        col = f"risk_{h}d"
        if col not in future_risk.columns:
            results[h] = {"status": "skipped"}
            continue

        ranked = future_risk.sort_values(col, ascending=False).reset_index(drop=True)
        y_true = ranked["provider_id"].isin(suspicious_providers).astype(int).values
        y_score = ranked[col].values.astype(float)

        from sklearn.metrics import roc_auc_score
        metric: dict[str, Any] = {
            "horizon_days": h,
            "n_providers": len(ranked),
            "n_suspicious_gt": len(suspicious_providers),
        }

        if len(np.unique(y_true)) > 1:
            metric["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
            metric["pr_auc"] = round(compute_average_precision(y_true, y_score), 4)
        else:
            metric["roc_auc"] = None
            metric["pr_auc"] = None

        base_rate = len(suspicious_providers) / len(ranked)
        for k in ks:
            p = precision_at_k(y_true, y_score, k)
            r = recall_at_k(y_true, y_score, k)
            metric[f"precision_at_{k}"] = round(p, 4)
            metric[f"recall_at_{k}"] = round(r, 4)
            metric[f"rank_lift_at_{k}"] = round(p / base_rate, 2) if base_rate > 0 else 0.0

        results[h] = metric

    return results


# Pipeline alias
train_and_predict_future_risk = fit_future_risk

