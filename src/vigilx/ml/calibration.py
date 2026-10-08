"""
Isotonic probability calibration for Vigil-X ML subsystem.

Calibrates raw LightGBM probability scores using provider-grouped
out-of-fold predictions.

CORE PRINCIPLES:
  1. No In-Sample Fitting: Calibrators are fitted strictly on out-of-fold
     predictions, never on in-sample training predictions.
  2. Strict Provider Non-Leakage: For any validation fold k, the calibrator
     evaluating fold k is fitted solely on out-of-fold predictions from
     the remaining folds j != k.
  3. Sample Size & Distribution Checks: Isotonic regression requires sufficient
     sample size and both classes represented. If a dataset is too small or
     degenerate, safe fallback clipping is applied.
  4. Honest Metric Reporting: Evaluates before vs after calibration across
     Brier score, ECE, log loss, PR-AUC, and ROC-AUC.
"""
from __future__ import annotations

import warnings
from typing import Any, Optional

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from vigilx.ml.metrics_utils import compute_average_precision


class IsotonicCalibrator:
    """
    Isotonic regression probability calibrator with distribution safety checks.

    Parameters
    ----------
    out_of_bounds : str, default 'clip'
        Handling for out-of-bounds input values in IsotonicRegression.
    y_min : float, default 0.0
        Minimum calibrated probability bound.
    y_max : float, default 1.0
        Maximum calibrated probability bound.
    min_samples : int, default 50
        Minimum sample size required to fit isotonic regression.
    min_positives : int, default 5
        Minimum positive class instances required to fit isotonic regression.
    """

    def __init__(
        self,
        out_of_bounds: str = "clip",
        y_min: float = 0.0,
        y_max: float = 1.0,
        min_samples: int = 50,
        min_positives: int = 5,
        min_positive_frac: Optional[float] = None,
    ) -> None:
        self.out_of_bounds = out_of_bounds
        self.y_min = y_min
        self.y_max = y_max
        self.min_samples = min_samples
        self.min_positives = min_positives
        self.min_positive_frac = min_positive_frac

        self._regressor: Optional[IsotonicRegression] = None
        self._fallback_method: Optional[str] = None
        self._is_fitted: bool = False
        self._n_samples: int = 0
        self._n_positives: int = 0

    def fit(self, y_score: np.ndarray, y_true: np.ndarray) -> "IsotonicCalibrator":
        """
        Fit isotonic regression on predicted scores and true binary targets.

        If sample size or class distribution is insufficient, falls back
        gracefully to identity clipping.
        """
        y_score = np.asarray(y_score, dtype=np.float64)
        y_true = np.asarray(y_true, dtype=np.int8)

        self._n_samples = len(y_score)
        self._n_positives = int(np.sum(y_true))
        n_unique_classes = len(np.unique(y_true))

        # Check sufficiency conditions
        min_pos = self.min_positives
        if self.min_positive_frac is not None:
            min_pos = max(min_pos, int(np.ceil(self._n_samples * self.min_positive_frac)))
        if (
            self._n_samples < self.min_samples
            or self._n_positives < min_pos
            or n_unique_classes < 2
        ):
            warnings.warn(
                f"Sample size ({self._n_samples}) or positive count ({self._n_positives}) "
                f"insufficient for isotonic regression (requires >={self.min_samples} samples, "
                f">={min_pos} positives, >=2 classes). "
                "Falling back to identity clipping.",
                UserWarning,
                stacklevel=2,
            )
            self._fallback_method = "identity"
            self._regressor = None
            self._is_fitted = True
            return self

        self._regressor = IsotonicRegression(
            out_of_bounds=self.out_of_bounds,
            y_min=self.y_min,
            y_max=self.y_max,
        )
        self._regressor.fit(y_score, y_true)
        self._fallback_method = None
        self._is_fitted = True
        return self

    def predict(self, y_score: np.ndarray) -> np.ndarray:
        """
        Map raw probability scores to calibrated probabilities.
        """
        if not self._is_fitted:
            raise RuntimeError("Calibrator is not fitted. Call fit() first.")

        y_score = np.asarray(y_score, dtype=np.float64)
        if self._fallback_method == "identity" or self._regressor is None:
            return np.clip(y_score, self.y_min, self.y_max)

        calibrated = self._regressor.predict(y_score)
        return np.clip(calibrated, self.y_min, self.y_max)

    def to_dict(self) -> dict[str, Any]:
        """Return serialisable calibration configuration and state."""
        return {
            "method": "IsotonicRegression" if self._fallback_method is None else "IdentityFallback",
            "out_of_bounds": self.out_of_bounds,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "min_samples": self.min_samples,
            "min_positives": self.min_positives,
            "is_fitted": self._is_fitted,
            "fallback_method": self._fallback_method,
            "n_samples": self._n_samples,
            "n_positives": self._n_positives,
        }


def calibrate_oof(
    oof_probs: np.ndarray,
    y: np.ndarray,
    fold_assignments: np.ndarray,
    n_folds: int = 5,
    min_samples: int = 50,
    min_positives: int = 5,
) -> tuple[np.ndarray, list[IsotonicCalibrator]]:
    """
    Perform leakage-free out-of-fold probability calibration.

    For each fold k:
      - Fits an IsotonicCalibrator strictly on out-of-fold predictions from
        folds j != k.
      - Applies the calibrator to fold k validation claims.
      - Guarantees fold k data and providers were not seen during fitting.

    Parameters
    ----------
    oof_probs : ndarray
        Raw out-of-fold predicted probabilities for all claims.
    y : ndarray
        Binary ground truth labels (0 or 1).
    fold_assignments : ndarray
        Fold ID (1 to n_folds) assigned to each claim.
    n_folds : int, default 5
        Total number of cross-validation folds.
    min_samples : int, default 50
        Minimum samples for isotonic fitting.
    min_positives : int, default 5
        Minimum positive samples for isotonic fitting.

    Returns
    -------
    calibrated_probs : ndarray of shape (n_claims,)
        Calibrated out-of-fold probabilities.
    fold_calibrators : list[IsotonicCalibrator]
        List of fold calibrators.
    """
    n_claims = len(oof_probs)
    calibrated_probs = np.full(n_claims, np.nan, dtype=np.float32)
    fold_calibrators: list[IsotonicCalibrator] = []

    unique_folds = sorted(int(f) for f in np.unique(fold_assignments) if f > 0)
    for fold in unique_folds:
        train_mask = fold_assignments != fold
        val_mask = fold_assignments == fold

        if not np.any(val_mask):
            continue

        cal = IsotonicCalibrator(min_samples=min_samples, min_positives=min_positives)
        cal.fit(oof_probs[train_mask], y[train_mask])

        calibrated_probs[val_mask] = cal.predict(oof_probs[val_mask]).astype(np.float32)
        fold_calibrators.append(cal)

    if np.isnan(calibrated_probs).any():
        missing_count = int(np.isnan(calibrated_probs).sum())
        raise RuntimeError(
            f"OOF calibration produced {missing_count} NaN values. "
            "Every claim must belong to a valid validation fold."
        )

    return calibrated_probs, fold_calibrators


def fit_final_calibrator(
    oof_probs: np.ndarray,
    y: np.ndarray,
    min_samples: int = 50,
    min_positives: int = 5,
) -> IsotonicCalibrator:
    """
    Fit a final calibrator using ALL out-of-fold predictions.

    Used for inference on unseen claims. Calibrating on OOF predictions
    avoids the overconfidence bias of in-sample training scores.
    """
    cal = IsotonicCalibrator(min_samples=min_samples, min_positives=min_positives)
    cal.fit(oof_probs, y)
    return cal


def compute_calibration_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[float, float, list[dict[str, Any]]]:
    """
    Compute Expected Calibration Error (ECE), Maximum Calibration Error (MCE),
    and bin-level reliability statistics.

    Parameters
    ----------
    y_true : ndarray
        Binary true labels (0 or 1).
    y_prob : ndarray
        Predicted probabilities in [0, 1].
    n_bins : int, default 10
        Number of equal-width probability bins.

    Returns
    -------
    (ece, mce, reliability_bins)
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)

    ece = 0.0
    mce = 0.0
    total = len(y_true)
    bins_data: list[dict[str, Any]] = []

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= low) & (y_prob <= high)
        else:
            mask = (y_prob >= low) & (y_prob < high)

        count = int(np.sum(mask))
        if count > 0:
            bin_acc = float(np.mean(y_true[mask]))
            bin_conf = float(np.mean(y_prob[mask]))
            diff = abs(bin_acc - bin_conf)
            ece += (count / total) * diff
            mce = max(mce, diff)
            bins_data.append({
                "bin": f"{low:.2f}-{high:.2f}",
                "count": count,
                "confidence": round(bin_conf, 4),
                "accuracy": round(bin_acc, 4),
                "gap": round(diff, 4),
            })
        else:
            bins_data.append({
                "bin": f"{low:.2f}-{high:.2f}",
                "count": 0,
                "confidence": 0.0,
                "accuracy": 0.0,
                "gap": 0.0,
            })

    return round(float(ece), 6), round(float(mce), 6), bins_data


def evaluate_calibration(
    y_true: np.ndarray,
    raw_probs: np.ndarray,
    calibrated_probs: np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]:
    """
    Evaluate calibration metrics comparing raw vs calibrated probabilities.

    Metrics reported:
      - Brier Score (mean squared error of probabilistic predictions)
      - Log Loss (binary cross-entropy)
      - Expected Calibration Error (ECE)
      - Maximum Calibration Error (MCE)
      - Mean predicted probability vs empirical positive prevalence
      - PR-AUC (Average Precision) before vs after
      - ROC-AUC before vs after
      - Bin-level reliability table
    """
    y_true = np.asarray(y_true, dtype=int)
    raw_probs = np.asarray(raw_probs, dtype=float)
    calibrated_probs = np.asarray(calibrated_probs, dtype=float)

    # Brier score (lower is better)
    brier_raw = float(brier_score_loss(y_true, raw_probs))
    brier_cal = float(brier_score_loss(y_true, calibrated_probs))

    # Log loss (lower is better)
    eps = 1e-15
    logloss_raw = float(log_loss(y_true, np.clip(raw_probs, eps, 1 - eps)))
    logloss_cal = float(log_loss(y_true, np.clip(calibrated_probs, eps, 1 - eps)))

    # ECE and MCE
    ece_raw, mce_raw, bins_raw = compute_calibration_curve(y_true, raw_probs, n_bins=n_bins)
    ece_cal, mce_cal, bins_cal = compute_calibration_curve(y_true, calibrated_probs, n_bins=n_bins)

    # Ranking preservation metrics
    pr_raw = compute_average_precision(y_true, raw_probs)
    pr_cal = compute_average_precision(y_true, calibrated_probs)

    roc_raw = float(roc_auc_score(y_true, raw_probs)) if len(np.unique(y_true)) > 1 else 0.5
    roc_cal = float(roc_auc_score(y_true, calibrated_probs)) if len(np.unique(y_true)) > 1 else 0.5

    mean_raw = float(np.mean(raw_probs))
    mean_cal = float(np.mean(calibrated_probs))
    empirical_rate = float(np.mean(y_true))

    return {
        "brier_score": {
            "before": round(brier_raw, 6),
            "after": round(brier_cal, 6),
            "delta": round(brier_cal - brier_raw, 6),
        },
        "log_loss": {
            "before": round(logloss_raw, 6),
            "after": round(logloss_cal, 6),
            "delta": round(logloss_cal - logloss_raw, 6),
        },
        "expected_calibration_error": {
            "before": ece_raw,
            "after": ece_cal,
            "delta": round(ece_cal - ece_raw, 6),
        },
        "max_calibration_error": {
            "before": mce_raw,
            "after": mce_cal,
        },
        "mean_predicted_probability": {
            "before": round(mean_raw, 6),
            "after": round(mean_cal, 6),
            "empirical_rate": round(empirical_rate, 6),
        },
        "pr_auc": {
            "before": round(pr_raw, 4),
            "after": round(pr_cal, 4),
        },
        "roc_auc": {
            "before": round(roc_raw, 4),
            "after": round(roc_cal, 4),
        },
        "reliability_bins_before": bins_raw,
        "reliability_bins_after": bins_cal,
    }
