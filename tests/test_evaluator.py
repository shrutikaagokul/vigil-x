"""
Tests for Rule Evaluator.

Covers:
  1. Metrics calculation without ground truth (volume, dollars, severities)
  2. Precision and recall calculation with ground truth claims
  3. Entity precision with ground truth providers
  4. JSON file export
"""

import json
import pandas as pd
import pytest

from eval.evaluator import evaluate_rules
from vigilx.models.alert import Alert, Severity


class TestEvaluator:

    def test_evaluator_without_ground_truth(self, tmp_path):
        """Evaluator computes summary stats when ground truth is absent."""
        alerts = [
            Alert(
                alert_id="A1",
                rule_id="R01",
                rule_version="1.0",
                entity_type="provider",
                entity_id="P1",
                claim_ids=["C1", "C2"],
                severity=Severity.HIGH,
                est_dollars=200.0,
                evidence=[],
            ),
            Alert(
                alert_id="A2",
                rule_id="R01",
                rule_version="1.0",
                entity_type="provider",
                entity_id="P2",
                claim_ids=["C3"],
                severity=Severity.MEDIUM,
                est_dollars=100.0,
                evidence=[],
            ),
        ]

        out_file = tmp_path / "metrics.json"
        metrics = evaluate_rules(alerts, output_path=out_file)

        assert metrics["total_alerts"] == 2
        assert metrics["total_claims_flagged"] == 3
        assert metrics["total_providers_flagged"] == 2
        assert metrics["total_est_dollars"] == 300.0
        assert metrics["rules"]["R01"]["num_alerts"] == 2

        # Check saved JSON
        with open(out_file) as f:
            saved = json.load(f)
            assert saved["total_alerts"] == 2

    def test_evaluator_with_ground_truth(self):
        """Precision and recall correctly computed against ground truth labels."""
        alerts = [
            Alert(
                alert_id="A1",
                rule_id="R01",
                rule_version="1.0",
                entity_type="provider",
                entity_id="P1",
                claim_ids=["C1", "C2"],  # C1 is true fraud, C2 is false positive
                severity=Severity.HIGH,
                est_dollars=150.0,
                evidence=[],
            )
        ]

        gt_claims = pd.DataFrame([
            {"claim_id": "C1", "rule_id": "R01", "is_fraud": True},
            {"claim_id": "C2", "rule_id": "R01", "is_fraud": False},
            {"claim_id": "C3", "rule_id": "R01", "is_fraud": True},  # Missed false negative
        ])

        gt_entities = pd.DataFrame([
            {"entity_id": "P1", "rule_id": "R01", "is_fraud": True},
        ])

        metrics = evaluate_rules(alerts, gt_claim_labels=gt_claims, gt_entity_labels=gt_entities)
        r01_m = metrics["rules"]["R01"]

        # Alert has {C1, C2}. GT fraud has {C1, C3}.
        # TP = C1 (1), FP = C2 (1), FN = C3 (1)
        assert r01_m["true_positives"] == 1
        assert r01_m["false_positives"] == 1
        assert r01_m["false_negatives"] == 1
        assert r01_m["precision"] == 0.5
        assert r01_m["recall"] == 0.5

        # Entity metrics
        assert r01_m["entity_true_positives"] == 1
        assert r01_m["entity_false_positives"] == 0
        assert r01_m["entity_precision"] == 1.0
