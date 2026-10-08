"""
Rule-level evaluation against ground truth for Vigil-X.

Ground truth is used ONLY for evaluation, NEVER for detection.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import pandas as pd

from contracts.alert import Alert


def evaluate_rules(
    alerts: List[Alert],
    gt_claim_labels: pd.DataFrame,
    gt_entity_labels: pd.DataFrame,
    gt_scenarios: pd.DataFrame,
    output_path: Optional[str] = None,
) -> Dict:
    """
    Evaluate R06-R10 alerts against ground truth.

    Reports per-rule:
    - alerts generated, affected claims, affected providers
    - true positives, false positives
    - precision, recall
    - exposure, detection by scenario
    """
    results = {}

    # Ground truth sets
    gt_suspicious_claims = set(
        gt_claim_labels[gt_claim_labels["is_suspicious"] == 1]["claim_id"]
    ) if not gt_claim_labels.empty else set()

    gt_suspicious_entities = set()
    if not gt_entity_labels.empty:
        for _, row in gt_entity_labels[gt_entity_labels["is_suspicious"] == 1].iterrows():
            gt_suspicious_entities.add((row["entity_type"], row["entity_id"]))

    # Scenario mapping
    scenario_rules = {}
    if not gt_scenarios.empty:
        for _, s in gt_scenarios.iterrows():
            for rule in str(s["expected_rules"]).split(","):
                scenario_rules.setdefault(rule.strip(), []).append(s["scenario_id"])

    # Group alerts by rule
    rules = ["R06", "R07", "R08", "R09", "R10"]
    for rule_id in rules:
        rule_alerts = [a for a in alerts if a.rule_id == rule_id]

        if not rule_alerts:
            results[rule_id] = {
                "alerts_generated": 0,
                "affected_claims": 0,
                "affected_providers": 0,
                "true_positives": 0,
                "false_positives": 0,
                "precision": 0,
                "recall": 0,
                "exposure": 0,
                "scenarios_detected": [],
            }
            continue

        alert_claims = set()
        alert_entities = set()
        for a in rule_alerts:
            alert_claims.update(a.claim_ids)
            alert_entities.add((a.entity_type, a.entity_id))

        # TP/FP at entity level
        tp_entities = alert_entities & gt_suspicious_entities
        fp_entities = alert_entities - gt_suspicious_entities
        tp = len(tp_entities)
        fp = len(fp_entities)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0

        # Recall: of all GT suspicious entities expected for this rule, how many did we find?
        expected_scenarios = scenario_rules.get(rule_id, [])
        gt_for_rule = set()
        if not gt_entity_labels.empty:
            for sid in expected_scenarios:
                matching = gt_entity_labels[
                    (gt_entity_labels["scenario_id"] == sid) &
                    (gt_entity_labels["is_suspicious"] == 1)
                ]
                for _, row in matching.iterrows():
                    gt_for_rule.add((row["entity_type"], row["entity_id"]))

        recall_denom = len(gt_for_rule) if gt_for_rule else 0
        recall_numer = len(alert_entities & gt_for_rule) if gt_for_rule else 0
        recall = recall_numer / recall_denom if recall_denom > 0 else 0

        # Exposure
        exposure = sum(a.est_dollars for a in rule_alerts)

        # Scenarios detected
        scenarios_detected = []
        for sid in expected_scenarios:
            scenario_entities = set()
            if not gt_entity_labels.empty:
                matching = gt_entity_labels[gt_entity_labels["scenario_id"] == sid]
                for _, row in matching.iterrows():
                    scenario_entities.add((row["entity_type"], row["entity_id"]))
            if alert_entities & scenario_entities:
                scenarios_detected.append(sid)

        results[rule_id] = {
            "alerts_generated": len(rule_alerts),
            "affected_claims": len(alert_claims),
            "affected_providers": len([e for e in alert_entities if e[0] == "provider"]),
            "true_positives": tp,
            "false_positives": fp,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "exposure": round(exposure, 2),
            "scenarios_detected": scenarios_detected,
        }

    # Summary
    total_alerts = len(alerts)
    total_tp = sum(r["true_positives"] for r in results.values())
    total_fp = sum(r["false_positives"] for r in results.values())

    output = {
        "summary": {
            "total_alerts": total_alerts,
            "total_true_positives": total_tp,
            "total_false_positives": total_fp,
            "overall_precision": round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0,
        },
        "per_rule": results,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

    return output
