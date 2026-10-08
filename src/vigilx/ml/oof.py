"""
Provider-grouped out-of-fold (OOF) cross-validation for Vigil-X.

WHY GROUPED OOF?
  Claims from the same provider share common billing templates, geographic
  location, speciality coding patterns, and latent fraud risk. Placing
  claims from Provider A in both train and validation would leak this
  shared structure, producing inflated validation metrics that do NOT
  generalise to held-out providers.

STRATEGY: GroupKFold by provider_id
  - All claims belonging to Provider A are placed entirely within one fold.
  - No provider appears in both the training set and the validation set
    for any fold.
  - Every claim receives exactly one out-of-fold prediction.

FOLD COUNT: 5
  At ~1,200 providers, 5 folds give ~240 providers per validation fold
  and ~960 providers for training. This provides sufficient training mass
  while still evaluating on a meaningful held-out provider set.

STRATIFICATION NOTE:
  sklearn's GroupKFold does not support joint group + label stratification.
  Since the positive class is ~0.3% (extremely imbalanced), we use
  StratifiedGroupKFold (available in sklearn ≥ 1.0) which tries to
  approximately preserve class balance across folds while maintaining the
  group constraint. If the dataset is too small for stratification to
  succeed, we fall back to plain GroupKFold with a warning.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Iterator

import numpy as np
import pandas as pd

try:
    from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
except ImportError as exc:
    raise ImportError(
        "scikit-learn >= 1.0 is required for StratifiedGroupKFold. "
        "Install it with: pip install 'scikit-learn>=1.3'"
    ) from exc


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

N_FOLDS: int = 5


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------


@dataclass
class FoldInfo:
    """Summary statistics for a single OOF fold."""
    fold: int
    train_providers: set[str]
    val_providers: set[str]
    train_claims: int
    val_claims: int
    train_positives: int
    val_positives: int
    train_positive_rate: float
    val_positive_rate: float

    # Invariant check
    provider_leakage: bool = field(init=False)

    def __post_init__(self) -> None:
        self.provider_leakage = bool(self.train_providers & self.val_providers)

    def summary(self) -> str:
        return (
            f"Fold {self.fold} | "
            f"Train: {self.train_claims:,} claims, {len(self.train_providers)} providers, "
            f"{self.train_positive_rate:.4%} positive | "
            f"Val: {self.val_claims:,} claims, {len(self.val_providers)} providers, "
            f"{self.val_positive_rate:.4%} positive | "
            f"Leakage: {self.provider_leakage}"
        )


# ------------------------------------------------------------------
# OOF split generator
# ------------------------------------------------------------------


def provider_grouped_kfold(
    X: pd.DataFrame,
    y: np.ndarray,
    provider_ids: pd.Series,
    n_splits: int = N_FOLDS,
    random_state: int = 42,
) -> Iterator[tuple[np.ndarray, np.ndarray, FoldInfo]]:
    """
    Yield provider-grouped out-of-fold (train_idx, val_idx) pairs.

    Guarantees:
      - For every fold, train_providers ∩ val_providers == ∅
      - Every claim appears in exactly one validation fold
      - Approximate class balance across folds (StratifiedGroupKFold)

    Parameters
    ----------
    X : DataFrame
        Feature matrix (index must align with y and provider_ids).
    y : ndarray of shape (n_claims,)
        Binary target labels (1 = suspicious, 0 = clean).
    provider_ids : Series of shape (n_claims,)
        Provider ID for each claim (grouping key).
    n_splits : int
        Number of folds (default 5).
    random_state : int
        Random seed for reproducibility.

    Yields
    ------
    (train_idx, val_idx, FoldInfo)
    """
    groups = provider_ids.values

    # Attempt StratifiedGroupKFold first for approximate class-balance preservation
    try:
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True,
                                         random_state=random_state)
        splits = list(splitter.split(X, y, groups=groups))
    except Exception as sgkf_err:
        warnings.warn(
            f"StratifiedGroupKFold failed ({sgkf_err}), "
            "falling back to GroupKFold (no stratification).",
            RuntimeWarning,
            stacklevel=2,
        )
        splitter = GroupKFold(n_splits=n_splits)
        splits = list(splitter.split(X, y, groups=groups))

    for fold_idx, (train_idx, val_idx) in enumerate(splits, start=1):
        train_providers = set(groups[train_idx].tolist())
        val_providers = set(groups[val_idx].tolist())

        train_y = y[train_idx]
        val_y = y[val_idx]

        info = FoldInfo(
            fold=fold_idx,
            train_providers=train_providers,
            val_providers=val_providers,
            train_claims=len(train_idx),
            val_claims=len(val_idx),
            train_positives=int(train_y.sum()),
            val_positives=int(val_y.sum()),
            train_positive_rate=float(train_y.mean()) if len(train_y) > 0 else 0.0,
            val_positive_rate=float(val_y.mean()) if len(val_y) > 0 else 0.0,
        )

        yield train_idx, val_idx, info


# ------------------------------------------------------------------
# Full OOF prediction runner
# ------------------------------------------------------------------


def generate_oof_predictions(
    X: pd.DataFrame,
    y: np.ndarray,
    provider_ids: pd.Series,
    train_fn,
    predict_fn,
    n_splits: int = N_FOLDS,
    random_state: int = 42,
) -> tuple[np.ndarray, list[FoldInfo], list]:
    """
    Generate out-of-fold predictions using provider-grouped cross-validation.

    Parameters
    ----------
    X : DataFrame
        Feature matrix (n_claims × n_features).
    y : ndarray
        Binary target (n_claims,).
    provider_ids : Series
        Provider ID per claim.
    train_fn : callable
        train_fn(X_train, y_train) -> model
    predict_fn : callable
        predict_fn(model, X_val) -> ndarray of probabilities (n_val,)
    n_splits : int
        OOF folds.
    random_state : int
        Seed.

    Returns
    -------
    oof_probs : ndarray of shape (n_claims,)
        Out-of-fold probability for every claim.
    fold_infos : list[FoldInfo]
        Fold statistics (use for leakage audit).
    fold_models : list
        List of fitted model objects (one per fold).
    """
    n = len(X)
    oof_probs = np.full(n, np.nan, dtype=np.float64)
    fold_infos: list[FoldInfo] = []
    fold_models: list = []

    X_arr = X.values if isinstance(X, pd.DataFrame) else X

    for train_idx, val_idx, info in provider_grouped_kfold(
        X, y, provider_ids, n_splits=n_splits, random_state=random_state
    ):
        X_train = X.iloc[train_idx]
        X_val = X.iloc[val_idx]
        y_train = y[train_idx]

        model = train_fn(X_train, y_train)
        probs = predict_fn(model, X_val)

        oof_probs[val_idx] = probs
        fold_infos.append(info)
        fold_models.append(model)

    # Sanity checks
    missing = np.sum(np.isnan(oof_probs))
    if missing > 0:
        raise RuntimeError(
            f"OOF generation incomplete: {missing} claims did not receive a prediction. "
            "This indicates a fold membership issue."
        )

    return oof_probs, fold_infos, fold_models


def validate_oof_integrity(
    fold_infos: list[FoldInfo],
    all_claim_indices: pd.Index,
    provider_ids: pd.Series,
) -> dict[str, object]:
    """
    Validate that OOF predictions satisfy the provider non-leakage guarantee.

    Returns a summary dict. Raises ValueError if leakage is detected.
    """
    leakage_folds = [fi for fi in fold_infos if fi.provider_leakage]
    if leakage_folds:
        raise ValueError(
            f"Provider leakage detected in folds: "
            f"{[fi.fold for fi in leakage_folds]}. "
            "This must not happen with GroupKFold."
        )

    return {
        "n_folds": len(fold_infos),
        "total_train_unique_providers": len(
            set().union(*[fi.train_providers for fi in fold_infos])
        ),
        "leakage_detected": False,
        "fold_summaries": [fi.summary() for fi in fold_infos],
    }
