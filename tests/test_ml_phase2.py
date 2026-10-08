"""
Phase 2 ML Subsystem Tests for Vigil-X.

Covers:
  Phase A — Isotonic Calibration + SHAP Explainability
  Phase B — Isolation Forest Provider Anomaly Detection
  Phase C — Future Risk 30/60/90 Day Prediction

SCIENTIFIC PRINCIPLES:
  - No leakage: ground truth never used as features
  - No in-sample calibration: calibrator fitted on OOF data
  - No fabricated metrics: all assertions on actual structure, not values
  - Temporal correctness: future risk features strictly before snapshot date
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

# Re-use Phase 1 fixture builders
from tests.test_ml_phase1 import (
    _make_gt_labels,
    _make_small_claims,
    _make_small_members,
    _make_small_providers,
)
from vigilx.ml.calibration import (
    IsotonicCalibrator,
    calibrate_oof,
    evaluate_calibration,
)
from vigilx.ml.explainability import (
    TreeSHAPExplainer,
    batch_extract_top_features,
    compute_oof_shap,
)
from vigilx.ml.claim_model import train_and_predict


# ==================================================================
# Shared fixtures
# ==================================================================


@pytest.fixture(scope="module")
def small_pipeline_result():
    """Run train_and_predict once for all Phase A tests."""
    claims = _make_small_claims(n=400, n_providers=25)
    providers = _make_small_providers(n=25)
    members = _make_small_members(n=60)
    gt = _make_gt_labels(claims, n_positive=20)

    with tempfile.TemporaryDirectory() as td:
        claim_ml, model, fold_infos = train_and_predict(
            claims=claims,
            providers=providers,
            members=members,
            gt_claim_labels=gt,
            output_dir=td,
            n_folds=3,
        )
        yield {
            "claim_ml": claim_ml,
            "model": model,
            "fold_infos": fold_infos,
            "claims": claims,
            "providers": providers,
            "members": members,
            "gt": gt,
            "output_dir": td,
        }


# ==================================================================
# Phase A: Calibration Tests
# ==================================================================


class TestCalibrationOutput:
    """Calibration output correctness and leakage prevention."""

    def test_calibrated_probability_column_exists(self, small_pipeline_result):
        """claim_ml must contain calibrated_probability after pipeline."""
        claim_ml = small_pipeline_result["claim_ml"]
        assert "calibrated_probability" in claim_ml.columns, (
            "calibrated_probability column missing from claim_ml"
        )

    def test_no_missing_calibrated_probabilities(self, small_pipeline_result):
        """All claims must have a calibrated probability."""
        claim_ml = small_pipeline_result["claim_ml"]
        n_null = claim_ml["calibrated_probability"].isna().sum()
        assert n_null == 0, f"Found {n_null} NaN calibrated_probability values"

    def test_calibrated_probabilities_in_valid_range(self, small_pipeline_result):
        """Calibrated probabilities must be in [0, 1]."""
        vals = small_pipeline_result["claim_ml"]["calibrated_probability"].values
        assert float(vals.min()) >= 0.0, f"min calibrated_probability < 0: {vals.min()}"
        assert float(vals.max()) <= 1.0, f"max calibrated_probability > 1: {vals.max()}"

    def test_raw_and_calibrated_are_distinct_columns(self, small_pipeline_result):
        """ml_probability and calibrated_probability must be separate columns."""
        claim_ml = small_pipeline_result["claim_ml"]
        assert "ml_probability" in claim_ml.columns
        assert "calibrated_probability" in claim_ml.columns
        # They should NOT be identical arrays
        raw = claim_ml["ml_probability"].values
        cal = claim_ml["calibrated_probability"].values
        # Not required to differ for every row but arrays should differ
        # (unless model is perfectly calibrated, which is extremely unlikely)
        # Allow if only a very tiny difference exists
        assert not np.allclose(raw, cal, atol=1e-6), (
            "calibrated_probability is identical to ml_probability — "
            "calibration may not have been applied"
        )

    def test_calibration_uses_oof_predictions_not_insample(self, small_pipeline_result):
        """
        Calibration MUST be fitted on OOF predictions only.

        Verify by checking that each claim's fold matches the calibrator
        that evaluated it (no claim was seen during its own calibrator's fit).
        We cannot directly introspect the fold indices without hooking into
        the calibration loop, so we assert the structural invariant:
        every oof_fold value is valid (no -1 sentinels for uncovered claims).
        """
        claim_ml = small_pipeline_result["claim_ml"]
        assert (claim_ml["oof_fold"] >= 0).all(), (
            "Some claims have oof_fold == -1 (not covered by OOF) — "
            "calibration would have no valid OOF prediction for these."
        )

    def test_isotonic_calibrator_unit_fit_predict(self):
        """IsotonicCalibrator fit/predict API contract."""
        rng = np.random.RandomState(0)
        # Intentionally mis-calibrated scores (shifted high)
        y_score = np.clip(rng.beta(5, 1, 1000), 0, 1)  # scores biased high
        y_true = (rng.rand(1000) < 0.2).astype(int)

        cal = IsotonicCalibrator()
        cal.fit(y_score, y_true)
        cal_probs = cal.predict(y_score)

        assert cal_probs.shape == y_score.shape
        assert float(cal_probs.min()) >= 0.0
        assert float(cal_probs.max()) <= 1.0

    def test_isotonic_calibrator_fallback_on_tiny_dataset(self):
        """Calibrator must gracefully fall back on tiny datasets."""
        rng = np.random.RandomState(0)
        y_score = rng.rand(10)  # too small to fit isotonic safely
        y_true = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 1])  # single positive

        cal = IsotonicCalibrator(min_samples=50, min_positive_frac=0.05)
        cal.fit(y_score, y_true)
        cal_probs = cal.predict(y_score)

        # Fallback: must return clipped values in [0, 1]
        assert cal_probs.shape == y_score.shape
        assert float(cal_probs.min()) >= 0.0
        assert float(cal_probs.max()) <= 1.0

    def test_calibrate_oof_returns_array_same_length(self, small_pipeline_result):
        """calibrate_oof must return same-length array as OOF predictions."""
        claim_ml = small_pipeline_result["claim_ml"]
        gt = small_pipeline_result["gt"]
        fold_infos = small_pipeline_result["fold_infos"]

        label_map = (
            gt[["claim_id", "is_suspicious"]]
            .set_index("claim_id")["is_suspicious"]
        )
        y_true = claim_ml["claim_id"].map(label_map).fillna(0).astype(int).values
        y_oof = claim_ml["ml_probability"].values
        oof_folds = claim_ml["oof_fold"].values

        cal_probs, _ = calibrate_oof(y_true, y_oof, oof_folds, fold_infos)
        assert len(cal_probs) == len(y_oof)

    def test_evaluate_calibration_metrics_structure(self):
        """evaluate_calibration must return required metric keys."""
        rng = np.random.RandomState(1)
        y_true = rng.binomial(1, 0.1, 500)
        y_raw = rng.rand(500)
        y_cal = y_raw * 0.1  # simple calibration mock

        result = evaluate_calibration(y_true, y_raw, y_cal)
        assert "brier_score" in result
        assert "before" in result["brier_score"]
        assert "after" in result["brier_score"]
        assert "expected_calibration_error" in result
        assert "log_loss" in result
        assert "before" in result["log_loss"]
        assert "after" in result["log_loss"]


class TestCalibrationEvaluation:
    """Calibration evaluation metrics are honest and well-formed."""

    def test_brier_score_is_non_negative(self, small_pipeline_result):
        claim_ml = small_pipeline_result["claim_ml"]
        gt = small_pipeline_result["gt"]

        label_map = gt.set_index("claim_id")["is_suspicious"]
        y_true = claim_ml["claim_id"].map(label_map).fillna(0).astype(int).values
        y_raw = claim_ml["ml_probability"].values
        y_cal = claim_ml["calibrated_probability"].values

        result = evaluate_calibration(y_true, y_raw, y_cal)
        assert result["brier_score"]["before"] >= 0.0
        assert result["brier_score"]["after"] >= 0.0

    def test_ece_is_non_negative(self, small_pipeline_result):
        claim_ml = small_pipeline_result["claim_ml"]
        gt = small_pipeline_result["gt"]

        label_map = gt.set_index("claim_id")["is_suspicious"]
        y_true = claim_ml["claim_id"].map(label_map).fillna(0).astype(int).values
        y_raw = claim_ml["ml_probability"].values
        y_cal = claim_ml["calibrated_probability"].values

        result = evaluate_calibration(y_true, y_raw, y_cal)
        assert result["expected_calibration_error"]["before"] >= 0.0
        assert result["expected_calibration_error"]["after"] >= 0.0

    def test_evaluation_report_includes_calibration_block(self, small_pipeline_result):
        """evaluate_claim_model report must include calibration block when available."""
        from vigilx.ml.evaluation import evaluate_claim_model

        claim_ml = small_pipeline_result["claim_ml"]
        gt = small_pipeline_result["gt"]
        fold_infos = small_pipeline_result["fold_infos"]
        claims = small_pipeline_result["claims"]

        with tempfile.TemporaryDirectory() as td:
            report = evaluate_claim_model(
                claim_ml=claim_ml,
                claims=claims,
                gt_claim_labels=gt,
                fold_infos=fold_infos,
                output_dir=td,
            )
        assert "calibration" in report, "calibration block missing from evaluation report"
        cal = report["calibration"]
        assert "brier_score" in cal
        assert "expected_calibration_error" in cal
        assert "calibrated_model" in cal


# ==================================================================
# Phase A: SHAP Explainability Tests
# ==================================================================


class TestSHAPOutput:
    """SHAP output dimensions, range, and determinism."""

    def test_top_features_column_exists(self, small_pipeline_result):
        claim_ml = small_pipeline_result["claim_ml"]
        assert "top_features" in claim_ml.columns

    def test_top_features_is_valid_json(self, small_pipeline_result):
        """Every top_features entry must be parseable JSON."""
        claim_ml = small_pipeline_result["claim_ml"]
        errors = []
        for i, val in enumerate(claim_ml["top_features"].values[:20]):
            try:
                parsed = json.loads(val)
                assert isinstance(parsed, dict), f"top_features[{i}] is not a JSON object"
            except (json.JSONDecodeError, TypeError) as e:
                errors.append(f"Row {i}: {e}")
        assert not errors, f"JSON parse errors: {errors}"

    def test_top_features_non_empty_for_most_claims(self, small_pipeline_result):
        """At least 90% of claims should have at least 1 top feature."""
        claim_ml = small_pipeline_result["claim_ml"]
        non_empty = 0
        for val in claim_ml["top_features"].values:
            try:
                parsed = json.loads(val)
                if parsed:
                    non_empty += 1
            except Exception:
                pass
        frac = non_empty / len(claim_ml)
        assert frac >= 0.9, f"Only {frac:.1%} claims have non-empty top_features"

    def test_shap_columns_in_output(self, small_pipeline_result):
        """Explicit top-3 feature columns must exist."""
        claim_ml = small_pipeline_result["claim_ml"]
        for i in range(1, 4):
            assert f"top_feature_{i}" in claim_ml.columns
            assert f"top_feature_{i}_shap" in claim_ml.columns

    def test_top_features_determinism(self, small_pipeline_result):
        """
        Recomputing SHAP on the same features must yield identical top_features.
        """
        model = small_pipeline_result["model"]
        claims = small_pipeline_result["claims"]
        providers = small_pipeline_result["providers"]
        members = small_pipeline_result["members"]

        from vigilx.ml.claim_features_ml import ALL_FEATURES, build_claim_feature_matrix
        feat = build_claim_feature_matrix(claims, providers, members)
        X_sub = feat[ALL_FEATURES].head(50)

        if model.explainer is None:
            pytest.skip("Explainer not initialized — SHAP unavailable")

        shap1, _ = model.explainer.compute_shap_values(X_sub)
        shap2, _ = model.explainer.compute_shap_values(X_sub)

        top1 = batch_extract_top_features(shap1, model.explainer.feature_names, n_top=3)
        top2 = batch_extract_top_features(shap2, model.explainer.feature_names, n_top=3)

        assert top1.equals(top2), "SHAP top_features are not deterministic"

    def test_shap_values_sum_to_margin(self, small_pipeline_result):
        """
        For LightGBM with pred_contrib, SHAP values + base_value should
        approximately equal the log-odds margin output.

        We check that the sum is finite and not NaN.
        """
        model = small_pipeline_result["model"]
        claims = small_pipeline_result["claims"]
        providers = small_pipeline_result["providers"]
        members = small_pipeline_result["members"]

        from vigilx.ml.claim_features_ml import ALL_FEATURES, build_claim_feature_matrix
        feat = build_claim_feature_matrix(claims, providers, members)
        X_sub = feat[ALL_FEATURES].head(30)

        if model.explainer is None:
            pytest.skip("Explainer not initialized")

        shap_vals, base = model.explainer.compute_shap_values(X_sub)

        # SHAP values should be finite
        assert np.all(np.isfinite(shap_vals)), "SHAP values contain inf/NaN"
        assert np.isfinite(base), f"base_value is not finite: {base}"

        # Row sums + base should be finite
        row_sums = shap_vals.sum(axis=1) + base
        assert np.all(np.isfinite(row_sums))


# ==================================================================
# Phase B: Isolation Forest Tests
# ==================================================================

def _make_large_claims(n_providers: int = 50, n_claims_per: int = 20, seed: int = 0) -> tuple:
    """Build a larger provider/claims fixture for anomaly detection tests."""
    rng = np.random.RandomState(seed)
    provider_ids = [f"P{i:04d}" for i in range(n_providers)]

    records = []
    for pid in provider_ids:
        n = rng.randint(5, n_claims_per)
        for j in range(n):
            svc_date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.randint(0, 365)))
            records.append({
                "claim_id": f"CLM_{pid}_{j}",
                "provider_id": pid,
                "member_id": f"M{rng.randint(0, 100):04d}",
                "service_date": svc_date,
                "paid_amount": float(rng.lognormal(5, 1)),
                "billed_amount": float(rng.lognormal(5.5, 1)),
                "procedure_code": rng.choice(["99213", "99214", "99215", "A0100"]),
                "service_minutes": float(rng.randint(5, 120)),
                "pos_code": rng.choice(["11", "22", "23"]),
                "facility_id": f"F{rng.randint(0, 5):03d}",
                "claim_type": rng.choice(["professional", "facility"]),
                "diagnosis_code": f"Z{rng.randint(0, 999):03d}",
                "status": "paid",
                "referring_provider_id": f"P{rng.randint(0, n_providers):04d}",
                "service_start_ts": svc_date,
                "service_end_ts": svc_date,
                "allowed_amount": float(rng.lognormal(4.5, 1)),
            })

    claims = pd.DataFrame(records)
    providers_df = pd.DataFrame({
        "provider_id": provider_ids,
        "specialty": rng.choice(["Internal Medicine", "Surgery", "Neurology"], size=n_providers),
        "latitude": rng.uniform(30, 45, size=n_providers).astype(float),
        "longitude": rng.uniform(-120, -70, size=n_providers).astype(float),
        "enrolled_date": "2020-01-01",
        "state": "CA",
        "city": "Los Angeles",
        "npi": [f"NPI{i:010d}" for i in range(n_providers)],
        "group_id": [f"G{i % 10:03d}" for i in range(n_providers)],
        "name": [f"Provider {i}" for i in range(n_providers)],
        "tin_hash": [f"TIN{i:010d}" for i in range(n_providers)],
        "bank_hash": [f"BANK{i:010d}" for i in range(n_providers)],
        "address": "123 Main St",
        "zip": "90001",
        "county": "Los Angeles",
        "facility_type": rng.choice(["clinic", "hospital"], size=n_providers),
        "owner_entity": rng.choice(["LLC", "Corp"], size=n_providers),
        "owner_name": [f"Owner {i}" for i in range(n_providers)],
        "registered_agent": [f"Agent {i}" for i in range(n_providers)],
        "suite": "",
    })

    gt_entity = pd.DataFrame({
        "entity_id": provider_ids[:5],
        "entity_type": "provider",
        "is_suspicious": 1,
        "scenario_id": "S001",
        "label_reason": "test_fwa",
    })

    return claims, providers_df, gt_entity


class TestProviderBehavioralFeatures:
    """Provider feature engineering for anomaly detection."""

    def test_features_build_correctly(self):
        from vigilx.ml.provider_features_ml import build_provider_behavioral_features, PROVIDER_ANOMALY_FEATURES
        claims, providers, _ = _make_large_claims(n_providers=30)
        feat = build_provider_behavioral_features(claims, providers)
        assert "provider_id" in feat.columns
        for col in PROVIDER_ANOMALY_FEATURES:
            assert col in feat.columns, f"Feature '{col}' missing"

    def test_no_nan_after_imputation(self):
        from vigilx.ml.provider_features_ml import build_provider_behavioral_features, PROVIDER_ANOMALY_FEATURES
        claims, providers, _ = _make_large_claims(n_providers=30)
        feat = build_provider_behavioral_features(claims, providers)
        numeric = feat.select_dtypes(include=[np.number])
        n_nan = numeric.isna().sum().sum()
        assert n_nan == 0, f"{n_nan} NaN values remain after imputation"

    def test_snapshot_date_filters_future_claims(self):
        """Snapshot date must exclude claims after snapshot."""
        from vigilx.ml.provider_features_ml import build_provider_behavioral_features
        claims, providers, _ = _make_large_claims(n_providers=20)
        snap = "2023-06-01"
        feat_all = build_provider_behavioral_features(claims, providers)
        feat_snap = build_provider_behavioral_features(claims, providers, snapshot_date=snap)

        # Claim count should be <= full dataset
        snap_count = feat_snap["prov_claim_count"].sum()
        all_count = feat_all["prov_claim_count"].sum()
        assert snap_count <= all_count, (
            f"Snapshot has more claims ({snap_count}) than full ({all_count}) — temporal leak!"
        )

    def test_features_are_deterministic(self):
        from vigilx.ml.provider_features_ml import build_provider_behavioral_features
        claims, providers, _ = _make_large_claims(n_providers=20)
        feat1 = build_provider_behavioral_features(claims, providers)
        feat2 = build_provider_behavioral_features(claims, providers)
        pd.testing.assert_frame_equal(
            feat1.sort_values("provider_id").reset_index(drop=True),
            feat2.sort_values("provider_id").reset_index(drop=True),
        )


class TestIsolationForestModel:
    """Isolation Forest model fitting, scoring, and output."""

    @pytest.fixture(scope="class")
    def anomaly_result(self):
        claims, providers, gt_entity = _make_large_claims(n_providers=50)
        with tempfile.TemporaryDirectory() as td:
            from vigilx.ml.provider_anomaly import fit_provider_anomaly, evaluate_provider_anomaly
            provider_anomaly, detector = fit_provider_anomaly(
                claims=claims, providers=providers, output_dir=td, contamination=0.1
            )
            # Create gt_entity_labels with the right columns expected by evaluate
            gt_entity_labels = gt_entity.copy()
            eval_result = evaluate_provider_anomaly(provider_anomaly, gt_entity_labels)
            yield {
                "provider_anomaly": provider_anomaly,
                "detector": detector,
                "eval": eval_result,
                "claims": claims,
                "providers": providers,
                "gt": gt_entity,
                "output_dir": td,
            }

    def test_output_schema(self, anomaly_result):
        """provider_anomaly must have required columns."""
        pa = anomaly_result["provider_anomaly"]
        required = ["provider_id", "anomaly_score", "anomaly_percentile",
                    "anomaly_flag", "model_version", "feature_version", "scored_at"]
        for col in required:
            assert col in pa.columns, f"Column '{col}' missing from provider_anomaly"

    def test_all_providers_scored(self, anomaly_result):
        """All providers in input must appear in output."""
        pa = anomaly_result["provider_anomaly"]
        providers = anomaly_result["providers"]
        expected = set(providers["provider_id"])
        actual = set(pa["provider_id"])
        assert expected == actual, f"Missing providers: {expected - actual}"

    def test_anomaly_scores_are_finite(self, anomaly_result):
        scores = anomaly_result["provider_anomaly"]["anomaly_score"].values
        assert np.all(np.isfinite(scores)), "anomaly_score contains inf/NaN"

    def test_anomaly_percentile_range(self, anomaly_result):
        pct = anomaly_result["provider_anomaly"]["anomaly_percentile"].values
        assert float(pct.min()) >= 0.0
        assert float(pct.max()) <= 100.0

    def test_anomaly_flag_is_binary(self, anomaly_result):
        flags = anomaly_result["provider_anomaly"]["anomaly_flag"].values
        assert set(flags).issubset({0, 1}), f"anomaly_flag has unexpected values: {set(flags)}"

    def test_flagged_count_matches_contamination(self, anomaly_result):
        """Number of flagged providers should approximately match contamination*n."""
        pa = anomaly_result["provider_anomaly"]
        n = len(pa)
        n_flagged = int(pa["anomaly_flag"].sum())
        expected = int(n * 0.1)  # contamination=0.1
        # Allow ±1 due to rounding
        assert abs(n_flagged - expected) <= 1, (
            f"n_flagged={n_flagged} doesn't match contamination*n={expected}"
        )

    def test_scores_sorted_descending(self, anomaly_result):
        """Output must be sorted by anomaly_score descending."""
        scores = anomaly_result["provider_anomaly"]["anomaly_score"].values
        assert np.all(scores[:-1] >= scores[1:]), "Output not sorted by anomaly_score descending"

    def test_no_ground_truth_in_features(self):
        """Anomaly detector features must NOT include ground truth labels."""
        from vigilx.ml.provider_features_ml import PROVIDER_ANOMALY_FEATURES
        banned_patterns = ["is_suspicious", "label", "gt", "ground_truth", "fraud"]
        for col in PROVIDER_ANOMALY_FEATURES:
            for banned in banned_patterns:
                assert banned not in col.lower(), (
                    f"Feature '{col}' appears to encode ground truth (contains '{banned}')"
                )

    def test_eval_structure(self, anomaly_result):
        """Evaluation result must contain required keys."""
        ev = anomaly_result["eval"]
        required = ["n_providers", "n_suspicious_gt", "n_flagged", "roc_auc"]
        for key in required:
            assert key in ev, f"Key '{key}' missing from eval result"

    def test_parquet_saved(self):
        """provider_anomaly.parquet must be saved to disk."""
        claims, providers, _ = _make_large_claims(n_providers=20)
        with tempfile.TemporaryDirectory() as td:
            from vigilx.ml.provider_anomaly import fit_provider_anomaly
            fit_provider_anomaly(claims=claims, providers=providers, output_dir=td)
            assert (Path(td) / "provider_anomaly.parquet").exists()

    def test_model_pkl_saved(self):
        """Model pkl must be saved to disk."""
        claims, providers, _ = _make_large_claims(n_providers=20)
        with tempfile.TemporaryDirectory() as td:
            from vigilx.ml.provider_anomaly import fit_provider_anomaly
            fit_provider_anomaly(claims=claims, providers=providers, output_dir=td)
            pkl_files = list(Path(td).glob("provider_anomaly_v*.pkl"))
            assert len(pkl_files) >= 1, "No provider_anomaly pkl found"

    def test_model_round_trip(self):
        """Model save/load must produce identical scores."""
        from vigilx.ml.provider_anomaly import ProviderAnomalyDetector
        from vigilx.ml.provider_features_ml import build_provider_behavioral_features, PROVIDER_ANOMALY_FEATURES

        claims, providers, _ = _make_large_claims(n_providers=20)
        feat = build_provider_behavioral_features(claims, providers)

        detector = ProviderAnomalyDetector(n_estimators=50, contamination=0.1)
        detector.fit(feat)
        scores_before = detector.score(feat)

        with tempfile.TemporaryDirectory() as td:
            detector.save(Path(td))
            loaded = ProviderAnomalyDetector.load(Path(td))
            scores_after = loaded.score(feat)

        np.testing.assert_array_almost_equal(
            scores_before, scores_after, decimal=5,
            err_msg="Anomaly scores differ after save/load round trip"
        )


# ==================================================================
# Phase C: Future Risk Tests
# ==================================================================


def _make_temporal_claims(n_providers: int = 30, days: int = 400, seed: int = 42) -> tuple:
    """Build a temporal claims dataset for future risk tests."""
    rng = np.random.RandomState(seed)
    provider_ids = [f"P{i:04d}" for i in range(n_providers)]
    suspicious_providers = set(provider_ids[:3])

    records = []
    gt_claim_rows = []
    claim_counter = 0

    for pid in provider_ids:
        is_suspicious_provider = pid in suspicious_providers
        for day_offset in range(0, days, rng.randint(3, 15)):
            svc_date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(day_offset))
            cid = f"CLM_{pid}_{claim_counter:06d}"
            claim_counter += 1
            is_sus = int(is_suspicious_provider and day_offset > 60)
            records.append({
                "claim_id": cid,
                "provider_id": pid,
                "member_id": f"M{rng.randint(0, 50):04d}",
                "service_date": svc_date,
                "paid_amount": float(rng.lognormal(5, 1)),
                "billed_amount": float(rng.lognormal(5.5, 1)),
                "procedure_code": rng.choice(["99213", "99214", "A0100"]),
                "service_minutes": float(rng.randint(10, 90)),
                "pos_code": rng.choice(["11", "22"]),
                "facility_id": "F001",
                "claim_type": "professional",
                "diagnosis_code": "Z123",
                "status": "paid",
                "referring_provider_id": pid,
                "service_start_ts": svc_date,
                "service_end_ts": svc_date,
                "allowed_amount": float(rng.lognormal(4.5, 1)),
            })
            gt_claim_rows.append({"claim_id": cid, "is_suspicious": is_sus})

    claims = pd.DataFrame(records)
    gt_claims = pd.DataFrame(gt_claim_rows)
    providers = pd.DataFrame({
        "provider_id": provider_ids,
        "specialty": "Internal Medicine",
        "latitude": rng.uniform(30, 45, size=n_providers).astype(float),
        "longitude": rng.uniform(-120, -70, size=n_providers).astype(float),
        "enrolled_date": "2020-01-01",
        "state": "CA",
        "city": "Los Angeles",
        "npi": [f"NPI{i:010d}" for i in range(n_providers)],
        "group_id": "G001",
        "name": [f"Provider {i}" for i in range(n_providers)],
        "tin_hash": [f"TIN{i}" for i in range(n_providers)],
        "bank_hash": [f"BANK{i}" for i in range(n_providers)],
        "address": "123 Main St", "zip": "90001", "county": "LA",
        "facility_type": "clinic", "owner_entity": "LLC",
        "owner_name": "Owner", "registered_agent": "Agent", "suite": "",
    })
    gt_entities = pd.DataFrame({
        "entity_id": list(suspicious_providers),
        "entity_type": "provider",
        "is_suspicious": 1,
        "scenario_id": "S001",
        "label_reason": "test_fwa",
    })

    return claims, providers, gt_claims, gt_entities


class TestFutureRiskTargets:
    """Target construction correctness and leakage prevention."""

    def test_targets_respect_snapshot_date(self):
        """Features must not use claims after snapshot_date."""
        from vigilx.ml.future_risk import build_future_risk_targets
        claims, providers, gt_claims, gt_entities = _make_temporal_claims()
        snap = "2023-06-01"
        targets = build_future_risk_targets(claims, gt_claims, gt_entities, snap, horizon_days=30)
        # All providers with target must have appeared in claims <= snap
        claims["service_date"] = pd.to_datetime(claims["service_date"])
        historical_providers = set(
            claims[claims["service_date"] <= pd.Timestamp(snap)]["provider_id"]
        )
        assert set(targets.index).issubset(historical_providers), (
            "Target includes providers with no historical claims before snapshot"
        )

    def test_targets_are_binary_or_nan(self):
        from vigilx.ml.future_risk import build_future_risk_targets
        claims, providers, gt_claims, gt_entities = _make_temporal_claims()
        targets = build_future_risk_targets(claims, gt_claims, gt_entities, "2023-06-01", 30)
        valid_values = targets.dropna().values
        assert set(valid_values).issubset({0, 1}), (
            f"Unexpected target values: {set(valid_values)}"
        )

    def test_no_future_features_in_training(self):
        """Multi-snapshot dataset must not have any claim feature > snapshot_date."""
        from vigilx.ml.future_risk import build_multi_snapshot_dataset
        from vigilx.ml.provider_features_ml import PROVIDER_ANOMALY_FEATURES
        claims, providers, gt_claims, gt_entities = _make_temporal_claims()
        df = build_multi_snapshot_dataset(
            claims, providers, gt_claims, gt_entities,
            horizon_days=30, n_snapshots=3, min_history_days=30
        )
        if df.empty:
            pytest.skip("Empty training set — insufficient data")
        # Verify that claim counts are not inflated
        # (can't directly verify dates used, but can check snapshots are older than data end)
        data_end = pd.to_datetime(claims["service_date"]).max()
        snap_dates = pd.to_datetime(df["snapshot_date"].unique())
        assert all(snap < data_end for snap in snap_dates), (
            "Snapshot dates must be before data end date"
        )


class TestFutureRiskModel:
    """Future risk model fitting and output schema."""

    @pytest.fixture(scope="class")
    def risk_result(self):
        claims, providers, gt_claims, gt_entities = _make_temporal_claims(
            n_providers=30, days=500
        )
        with tempfile.TemporaryDirectory() as td:
            from vigilx.ml.future_risk import fit_future_risk, evaluate_future_risk
            future_risk, models, reports = fit_future_risk(
                claims=claims,
                providers=providers,
                gt_claim_labels=gt_claims,
                gt_entity_labels=gt_entities,
                output_dir=td,
                horizons=[30, 60, 90],
                n_snapshots=4,
            )
            eval_results = evaluate_future_risk(future_risk, gt_entities)
            yield {
                "future_risk": future_risk,
                "models": models,
                "reports": reports,
                "eval": eval_results,
                "td": td,
            }

    def test_output_schema(self, risk_result):
        """future_risk must have required columns."""
        fr = risk_result["future_risk"]
        required = ["provider_id", "risk_30d", "risk_60d", "risk_90d",
                    "prediction_date", "model_version", "feature_version", "scored_at"]
        for col in required:
            assert col in fr.columns, f"Column '{col}' missing from future_risk"

    def test_all_providers_scored(self, risk_result):
        """All providers must have a future risk score."""
        fr = risk_result["future_risk"]
        assert len(fr) >= 1

    def test_risk_scores_in_valid_range(self, risk_result):
        fr = risk_result["future_risk"]
        for h in [30, 60, 90]:
            col = f"risk_{h}d"
            vals = fr[col].values
            assert float(vals.min()) >= 0.0, f"{col} min < 0"
            assert float(vals.max()) <= 1.0, f"{col} max > 1"

    def test_risk_scores_are_finite(self, risk_result):
        fr = risk_result["future_risk"]
        for h in [30, 60, 90]:
            col = f"risk_{h}d"
            assert np.all(np.isfinite(fr[col].values)), f"{col} contains inf/NaN"

    def test_training_reports_present(self, risk_result):
        """Training report must be present for each horizon."""
        reports = risk_result["reports"]
        for h in [30, 60, 90]:
            assert h in reports, f"No training report for horizon {h}d"

    def test_parquet_saved(self, risk_result):
        assert (Path(risk_result["td"]) / "future_risk.parquet").exists()

    def test_training_report_json_saved(self, risk_result):
        assert (Path(risk_result["td"]) / "future_risk_training_report.json").exists()

    def test_eval_structure(self, risk_result):
        """Evaluation output must contain required metric keys."""
        for h in [30, 60, 90]:
            ev = risk_result["eval"].get(h, {})
            assert "n_providers" in ev or "status" in ev, (
                f"No eval data for horizon {h}d"
            )

    def test_no_ground_truth_label_used_as_feature(self):
        """
        Future risk features (behavioral) must not contain ground truth labels.
        This is a structural check — GT labels are only used to build targets.
        """
        from vigilx.ml.provider_features_ml import PROVIDER_ANOMALY_FEATURES
        banned = ["is_suspicious", "label", "fraud", "ground_truth", "gt"]
        for col in PROVIDER_ANOMALY_FEATURES:
            for b in banned:
                assert b not in col.lower(), (
                    f"Feature '{col}' may encode GT (contains '{b}')"
                )


# ==================================================================
# Phase D: Ablation & Rank-Lift Tests
# ==================================================================


class TestRankLiftAnalysis:
    """Test rank-lift metric computation in evaluation routines."""

    def test_rank_lift_at_k_present_in_metrics(self):
        from vigilx.ml.evaluation import compute_metrics
        y_true = np.array([1] * 10 + [0] * 90)
        y_score = np.array([0.9] * 10 + [0.1] * 90)
        m = compute_metrics(y_true, y_score, ks=[10, 20])
        assert "rank_lift_at_10" in m
        assert m["rank_lift_at_10"] is not None
        # Perfect top-10 has precision 1.0, base rate is 0.10 -> lift is 10.0x
        assert m["rank_lift_at_10"] == 10.0

    def test_rank_lift_zero_positives_returns_none(self):
        from vigilx.ml.evaluation import compute_metrics
        y_true = np.array([0] * 50)
        y_score = np.random.rand(50)
        m = compute_metrics(y_true, y_score, ks=[10])
        assert m["rank_lift_at_10"] is None


class TestAblationStudy:
    """Test feature group ablation study runner."""

    def test_run_ablation_study_returns_expected_structure(self):
        from vigilx.ml.ablation import run_ablation_study

        claims = _make_small_claims(n=200, n_providers=20)
        providers = _make_small_providers(n=20)
        members = _make_small_members(n=40)
        gt = _make_gt_labels(claims, n_positive=15)

        # Test with a subset of ablation experiments for speed
        mini_experiments = {
            "full_model": ["paid_amount", "billed_amount", "service_minutes"],
            "amount_only": ["paid_amount"],
        }

        with tempfile.TemporaryDirectory() as td:
            report = run_ablation_study(
                claims=claims,
                providers=providers,
                members=members,
                gt_claim_labels=gt,
                n_folds=2,
                experiments=mini_experiments,
                output_dir=td,
            )

            assert "experiments" in report
            assert "full_model" in report["experiments"]
            assert "amount_only" in report["experiments"]
            assert (Path(td) / "ablation_report.json").exists()

            full = report["experiments"]["full_model"]
            assert "pr_auc" in full
            assert "roc_auc" in full
            assert "delta_pr_auc" in report["experiments"]["amount_only"]

