"""
Rule precision evaluator for Vigil-X.

Compares alerts against ground truth labels to compute per-rule metrics.
Ground truth is ONLY used here for evaluation — NEVER for detection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from vigilx.models.alert import Alert


def evaluate_rules(
    alerts: list[Alert],
    gt_claim_labels: pd.DataFrame | None = None,
    gt_entity_labels: pd.DataFrame | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Evaluate rule-generated alerts against ground truth.

    Parameters
    ----------
    alerts : list[Alert]
        Alerts produced by the detection subsystem.
    gt_claim_labels : DataFrame, optional
        Ground truth claim labels with columns: claim_id, rule_id, is_fraud.
    gt_entity_labels : DataFrame, optional
        Ground truth entity labels with columns: entity_id, rule_id, is_fraud.
    output_path : Path, optional
        If provided, save metrics JSON to this path.

    Returns
    -------
    dict with per-rule and overall metrics.
    """
    if not alerts:
        return {"total_alerts": 0, "rules": {}}

    # Group alerts by rule
    by_rule: dict[str, list[Alert]] = {}
    for alert in alerts:
        by_rule.setdefault(alert.rule_id, []).append(alert)

    metrics: dict[str, Any] = {
        "total_alerts": len(alerts),
        "rules": {},
    }

    for rule_id, rule_alerts in sorted(by_rule.items()):
        rule_metrics = _compute_rule_metrics(
            rule_id, rule_alerts, gt_claim_labels, gt_entity_labels,
        )
        metrics["rules"][rule_id] = rule_metrics

    # Overall
    metrics["total_claims_flagged"] = len(set(
        cid for alert in alerts for cid in alert.claim_ids
    ))
    metrics["total_providers_flagged"] = len(set(
        alert.entity_id for alert in alerts if alert.entity_type == "provider"
    ))
    metrics["total_est_dollars"] = round(sum(a.est_dollars for a in alerts), 2)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)

    return metrics


def _compute_rule_metrics(
    rule_id: str,
    rule_alerts: list[Alert],
    gt_claim_labels: pd.DataFrame | None,
    gt_entity_labels: pd.DataFrame | None,
) -> dict[str, Any]:
    """Compute metrics for a single rule."""
    alert_claim_ids = set(cid for a in rule_alerts for cid in a.claim_ids)
    alert_entity_ids = set(a.entity_id for a in rule_alerts)
    alert_providers = set(
        a.entity_id for a in rule_alerts if a.entity_type == "provider"
    )

    result: dict[str, Any] = {
        "num_alerts": len(rule_alerts),
        "num_claims_flagged": len(alert_claim_ids),
        "num_providers_flagged": len(alert_providers),
        "est_dollars_flagged": round(sum(a.est_dollars for a in rule_alerts), 2),
        "severity_distribution": _severity_dist(rule_alerts),
    }

    # Compute precision/recall if ground truth available
    if gt_claim_labels is not None and not gt_claim_labels.empty:
        gt_rule = gt_claim_labels[gt_claim_labels["rule_id"] == rule_id]
        if not gt_rule.empty:
            gt_fraud = set(gt_rule[gt_rule["is_fraud"] == True]["claim_id"].astype(str))  # noqa: E712
            gt_all = set(gt_rule["claim_id"].astype(str))

            tp = len(alert_claim_ids & gt_fraud)
            fp = len(alert_claim_ids - gt_fraud)
            fn = len(gt_fraud - alert_claim_ids)

            result["true_positives"] = tp
            result["false_positives"] = fp
            result["false_negatives"] = fn
            result["precision"] = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
            result["recall"] = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0

    if gt_entity_labels is not None and not gt_entity_labels.empty:
        gt_rule = gt_entity_labels[gt_entity_labels["rule_id"] == rule_id]
        if not gt_rule.empty:
            gt_fraud_entities = set(
                gt_rule[gt_rule["is_fraud"] == True]["entity_id"].astype(str)  # noqa: E712
            )
            entity_tp = len(alert_entity_ids & gt_fraud_entities)
            entity_fp = len(alert_entity_ids - gt_fraud_entities)
            result["entity_true_positives"] = entity_tp
            result["entity_false_positives"] = entity_fp
            result["entity_precision"] = round(
                entity_tp / (entity_tp + entity_fp), 4
            ) if (entity_tp + entity_fp) > 0 else 0.0

    return result


def _severity_dist(alerts: list[Alert]) -> dict[str, int]:
    """Count alerts by severity."""
    dist: dict[str, int] = {}
    for a in alerts:
        dist[a.severity.value] = dist.get(a.severity.value, 0) + 1
    return dist
