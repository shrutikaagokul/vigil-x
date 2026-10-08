"""
Shared metric utilities for the Vigil-X ML subsystem.

Kept in a separate module to avoid circular imports between
calibration.py and evaluation.py.
"""
from __future__ import annotations

import numpy as np


def compute_average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """
    Compute uninterpolated average precision (PR-AUC) robustly.

    Avoids Python 3.14 borrowed-refcount memory reuse bug in scikit-learn
    where binary_op (+) mutates tps in-place for arrays >= 32,768 elements.
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    desc_indices = np.argsort(y_score, kind="mergesort")[::-1]
    y_true_sorted = y_true[desc_indices]
    tps = np.cumsum(y_true_sorted)
    n_pos = tps[-1]
    if n_pos == 0:
        return 0.0
    ranks = np.arange(1, len(y_true) + 1)
    precisions = tps / ranks
    return float(np.sum(precisions * y_true_sorted) / n_pos)


def precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of true positives in the top-K scored items."""
    if k <= 0 or len(y_true) == 0:
        return 0.0
    k = min(k, len(y_true))
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true[top_k_idx].sum()) / k


def recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of all true positives captured in the top-K scored items."""
    if k <= 0 or len(y_true) == 0:
        return 0.0
    total_positive = y_true.sum()
    if total_positive == 0:
        return 0.0
    k = min(k, len(y_true))
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true[top_k_idx].sum()) / float(total_positive)
