"""
Tests for Vigil-X Phase 1 ML subsystem.

Covers:
  - Feature matrix assembly (correctness, missing values, categorical handling)
  - Target label preparation (no leakage)
  - Provider grouping (OOF fold disjointness)
  - OOF integrity (every claim gets exactly one prediction)
  - Provider leakage: intersection(train_providers, val_providers) == ∅
  - Output schema (claim_ml contract)
  - Determinism
  - Model training on small fixture
  - Evaluation metrics (P@K, R@K, PR-AUC, ROC-AUC)
"""
from __future__ import annotations

import json
import pickle
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_small_claims(n: int = 200, n_providers: int = 20, seed: int = 0) -> pd.DataFrame:
    """Create a minimal claims DataFrame for unit tests."""
    rng = np.random.RandomState(seed)
    providers = [f"P{i:04d}" for i in range(n_providers)]
    members = [f"M{i:06d}" for i in range(50)]
    pos_codes = ["11", "22", "02", "10"]
    claim_types = ["professional", "institutional"]

    records = []
    for i in range(n):
        pid = rng.choice(providers)
        mid = rng.choice(members)
        paid = round(float(rng.lognormal(4.5, 1.0)), 2)
        billed = round(paid * rng.uniform(1.1, 1.5), 2)
        svc_date = f"2023-{rng.randint(1, 13):02d}-{rng.randint(1, 28):02d}"
        records.append({
            "claim_id": f"C{i:07d}",
            "member_id": mid,
            "provider_id": pid,
            "facility_id": f"F{rng.randint(1, 10):04d}" if rng.random() > 0.3 else None,
            "referring_provider_id": f"P{rng.randint(0, n_providers):04d}" if rng.random() < 0.15 else None,
            "service_date": svc_date,
            "service_start_ts": f"{svc_date} 09:00:00",
            "service_end_ts": f"{svc_date} 09:30:00",
            "service_minutes": int(rng.choice([15, 30, 45, 60])),
            "pos_code": rng.choice(pos_codes),
            "procedure_code": rng.choice(["CPT99213", "CPT99214", "CPT99215", "CPT80053"]),
            "diagnosis_code": f"ICD{rng.randint(1, 100):03d}",
            "paid_amount": paid,
            "billed_amount": billed,
            "allowed_amount": round(paid * 1.05, 2),
            "status": "paid",
            "claim_type": rng.choice(claim_types),
        })
    return pd.DataFrame(records)


def _make_small_providers(n: int = 20) -> pd.DataFrame:
    specialties = ["family_medicine", "cardiology", "radiology", "orthopedics"]
    return pd.DataFrame([{
        "provider_id": f"P{i:04d}",
        "specialty": specialties[i % len(specialties)],
        "latitude": 33.0 + (i % 5) * 0.1,
        "longitude": -84.0 + (i % 5) * 0.1,
    } for i in range(n)])


def _make_small_members(n: int = 50) -> pd.DataFrame:
    return pd.DataFrame([{
        "member_id": f"M{i:06d}",
        "latitude": 33.5 + (i % 5) * 0.1,
        "longitude": -83.5 + (i % 5) * 0.1,
    } for i in range(n)])


def _make_gt_labels(claims: pd.DataFrame, n_positive: int = 10) -> pd.DataFrame:
    """Mark the first n_positive claims as suspicious."""
    suspicious_ids = claims["claim_id"].iloc[:n_positive].tolist()
    return pd.DataFrame([{
        "claim_id": cid,
        "scenario_id": "S001",
        "is_suspicious": 1,
        "label_reason": "test",
    } for cid in suspicious_ids])


# ------------------------------------------------------------------
# Feature Matrix Tests
# ------------------------------------------------------------------


class TestFeatureMatrix:
    def setup_method(self):
        self.claims = _make_small_claims(n=200, n_providers=20)
        self.providers = _make_small_providers(n=20)
        self.members = _make_small_members(n=50)

    def test_returns_dataframe(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        assert isinstance(feat, pd.DataFrame)

    def test_row_count_matches_claims(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        assert len(feat) == len(self.claims)

    def test_required_key_columns_present(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        assert "claim_id" in feat.columns
        assert "provider_id" in feat.columns

    def test_all_feature_columns_present(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        for col in ALL_FEATURES:
            assert col in feat.columns, f"Missing feature column: {col}"

    def test_no_nan_in_numeric_features(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, NUMERIC_FEATURES
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        for col in NUMERIC_FEATURES:
            n_nan = feat[col].isna().sum()
            assert n_nan == 0, f"NaN found in numeric feature '{col}': {n_nan} NaN values"

    def test_no_nan_in_categorical_features(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, CATEGORICAL_FEATURES
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        for col in CATEGORICAL_FEATURES:
            n_nan = feat[col].isna().sum()
            assert n_nan == 0, f"NaN found in categorical feature '{col}': {n_nan} NaN values"

    def test_paid_to_billed_ratio_bounds(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        assert feat["paid_to_billed_ratio"].min() >= 0.0
        assert feat["paid_to_billed_ratio"].max() <= 2.0

    def test_em_level_is_valid(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        valid = feat["em_level"].isin([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        assert valid.all(), f"Unexpected em_level values: {feat['em_level'].unique()}"

    def test_is_weekend_binary(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        assert feat["is_weekend"].isin([0.0, 1.0]).all()

    def test_has_facility_binary(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        assert feat["has_facility"].isin([0.0, 1.0]).all()

    def test_empty_claims_returns_empty_frame(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        empty = pd.DataFrame(columns=self.claims.columns)
        feat = build_claim_feature_matrix(empty, self.providers, self.members)
        assert feat.empty or len(feat) == 0

    def test_leakage_columns_absent(self):
        """Ground truth and ID columns must never appear in the feature matrix."""
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        forbidden = {
            "is_suspicious", "scenario_id", "label_reason",
            "member_id", "facility_id", "referring_provider_id",
            "rule_id", "alert_id", "est_dollars",
        }
        for col in forbidden:
            assert col not in feat.columns, f"Leakage column '{col}' found in feature matrix!"

    def test_categorical_features_are_categorical(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, CATEGORICAL_FEATURES
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        for col in CATEGORICAL_FEATURES:
            assert feat[col].dtype.name == "category", f"Categorical '{col}' is not category dtype"

    def test_missing_provider_coords_handled(self):
        """When providers have no lat/lon, dist should fill with 0."""
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        prov_no_geo = self.providers.drop(columns=["latitude", "longitude"])
        feat = build_claim_feature_matrix(self.claims, prov_no_geo, self.members)
        assert "dist_member_provider_miles" in feat.columns
        # Should not raise; fill with 0.0
        assert feat["dist_member_provider_miles"].isna().sum() == 0

    def test_deterministic_output(self):
        """Same inputs → same outputs (feature matrix is deterministic)."""
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, NUMERIC_FEATURES
        feat1 = build_claim_feature_matrix(self.claims, self.providers, self.members)
        feat2 = build_claim_feature_matrix(self.claims, self.providers, self.members)
        for col in NUMERIC_FEATURES:
            assert feat1[col].equals(feat2[col]), f"Non-deterministic column: {col}"


# ------------------------------------------------------------------
# Target Preparation Tests
# ------------------------------------------------------------------


class TestTargetPreparation:
    def setup_method(self):
        self.claims = _make_small_claims(n=100, n_providers=10)

    def test_target_length_matches_claims(self):
        from vigilx.ml.claim_model import prepare_target
        gt = _make_gt_labels(self.claims, n_positive=5)
        y = prepare_target(self.claims, gt)
        assert len(y) == len(self.claims)

    def test_target_is_binary(self):
        from vigilx.ml.claim_model import prepare_target
        gt = _make_gt_labels(self.claims, n_positive=5)
        y = prepare_target(self.claims, gt)
        assert set(y.tolist()).issubset({0, 1})

    def test_target_positive_count_matches_gt(self):
        from vigilx.ml.claim_model import prepare_target
        n_pos = 5
        gt = _make_gt_labels(self.claims, n_positive=n_pos)
        y = prepare_target(self.claims, gt)
        assert y.sum() == n_pos

    def test_empty_gt_gives_all_zeros(self):
        from vigilx.ml.claim_model import prepare_target
        y = prepare_target(self.claims, pd.DataFrame())
        assert y.sum() == 0
        assert len(y) == len(self.claims)

    def test_gt_columns_not_in_feature_space(self):
        """GT labels must not bleed into the feature matrix."""
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix
        from vigilx.ml.claim_model import prepare_target
        providers = _make_small_providers(10)
        members = _make_small_members(50)
        gt = _make_gt_labels(self.claims, n_positive=5)

        # Build feature matrix WITHOUT passing gt
        feat = build_claim_feature_matrix(self.claims, providers, members)
        # Confirm ground truth columns are absent
        assert "is_suspicious" not in feat.columns
        assert "label_reason" not in feat.columns


# ------------------------------------------------------------------
# OOF Provider Grouping Tests  ← MOST IMPORTANT
# ------------------------------------------------------------------


class TestOOFProviderGrouping:
    """
    Critical property: For every OOF fold,
        train_providers ∩ val_providers == ∅
    """

    def setup_method(self):
        self.claims = _make_small_claims(n=300, n_providers=30)
        self.providers = _make_small_providers(n=30)
        self.members = _make_small_members(n=50)
        self.gt = _make_gt_labels(self.claims, n_positive=15)

    def test_no_provider_leakage_in_any_fold(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import prepare_target
        from vigilx.ml.oof import provider_grouped_kfold

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        provider_ids = feat["provider_id"]
        X = feat[ALL_FEATURES]

        leakage_folds = []
        for train_idx, val_idx, fi in provider_grouped_kfold(X, y, provider_ids, n_splits=5):
            train_prov = set(provider_ids.iloc[train_idx].tolist())
            val_prov = set(provider_ids.iloc[val_idx].tolist())
            intersection = train_prov & val_prov
            if intersection:
                leakage_folds.append((fi.fold, intersection))

        assert len(leakage_folds) == 0, (
            f"Provider leakage detected in folds: {leakage_folds}"
        )

    def test_every_claim_gets_exactly_one_oof_prediction(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import prepare_target
        from vigilx.ml.oof import provider_grouped_kfold

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        provider_ids = feat["provider_id"]
        X = feat[ALL_FEATURES]

        prediction_count = np.zeros(len(feat), dtype=int)
        for train_idx, val_idx, fi in provider_grouped_kfold(X, y, provider_ids, n_splits=5):
            prediction_count[val_idx] += 1

        assert (prediction_count == 1).all(), (
            f"Some claims got wrong prediction count: "
            f"min={prediction_count.min()}, max={prediction_count.max()}"
        )

    def test_fold_count_matches_n_splits(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import prepare_target
        from vigilx.ml.oof import provider_grouped_kfold

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        X = feat[ALL_FEATURES]

        folds = list(provider_grouped_kfold(X, y, feat["provider_id"], n_splits=5))
        assert len(folds) == 5

    def test_fold_info_leakage_attribute_is_false(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import prepare_target
        from vigilx.ml.oof import provider_grouped_kfold

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        X = feat[ALL_FEATURES]

        for _, _, fi in provider_grouped_kfold(X, y, feat["provider_id"], n_splits=5):
            assert fi.provider_leakage is False, (
                f"FoldInfo reports leakage in fold {fi.fold}: "
                f"{fi.train_providers & fi.val_providers}"
            )

    def test_validate_oof_integrity_passes(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import prepare_target
        from vigilx.ml.oof import (
            FoldInfo,
            provider_grouped_kfold,
            validate_oof_integrity,
        )

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        X = feat[ALL_FEATURES]
        pids = feat["provider_id"]

        fold_infos = [fi for _, _, fi in provider_grouped_kfold(X, y, pids, n_splits=5)]
        audit = validate_oof_integrity(fold_infos, feat.index, pids)
        assert audit["leakage_detected"] is False
        assert audit["n_folds"] == 5

    def test_provider_coverage_across_all_folds(self):
        """Every provider should appear in exactly one validation fold."""
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import prepare_target
        from vigilx.ml.oof import provider_grouped_kfold

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        X = feat[ALL_FEATURES]
        pids = feat["provider_id"]

        all_providers = set(pids.unique())
        val_provider_union: set[str] = set()
        val_provider_count: dict[str, int] = {}

        for _, val_idx, fi in provider_grouped_kfold(X, y, pids, n_splits=5):
            for p in fi.val_providers:
                val_provider_count[p] = val_provider_count.get(p, 0) + 1
                val_provider_union.add(p)

        # All providers seen in at least one val fold
        assert val_provider_union == all_providers, (
            f"Providers not covered in any val fold: {all_providers - val_provider_union}"
        )
        # Each provider appears in exactly one val fold
        over_counted = {p: cnt for p, cnt in val_provider_count.items() if cnt > 1}
        assert len(over_counted) == 0, (
            f"Providers appearing in multiple val folds (leakage): {over_counted}"
        )


# ------------------------------------------------------------------
# Model Training Tests
# ------------------------------------------------------------------


class TestModelTraining:
    def setup_method(self):
        # Use small fixture for fast tests
        self.claims = _make_small_claims(n=300, n_providers=30)
        self.providers = _make_small_providers(n=30)
        self.members = _make_small_members(n=50)
        self.gt = _make_gt_labels(self.claims, n_positive=20)

    def test_fit_oof_returns_probabilities(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import ClaimRiskModel, prepare_target

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)

        model = ClaimRiskModel(n_folds=3)  # fewer folds for speed
        oof_probs = model.fit_oof(feat[ALL_FEATURES], y, feat["provider_id"])

        assert len(oof_probs) == len(feat)
        assert oof_probs.min() >= 0.0
        assert oof_probs.max() <= 1.0
        assert not np.any(np.isnan(oof_probs)), "OOF probs contain NaN"

    def test_model_is_fitted_after_fit_oof(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import ClaimRiskModel, prepare_target

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        model = ClaimRiskModel(n_folds=3)
        model.fit_oof(feat[ALL_FEATURES], y, feat["provider_id"])
        assert model._is_fitted

    def test_fold_models_count_matches_n_folds(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import ClaimRiskModel, prepare_target

        n_folds = 3
        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        model = ClaimRiskModel(n_folds=n_folds)
        model.fit_oof(feat[ALL_FEATURES], y, feat["provider_id"])
        assert len(model._fold_models) == n_folds

    def test_train_final_enables_predict(self):
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import ClaimRiskModel, prepare_target

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)
        model = ClaimRiskModel(n_folds=3)
        model.fit_oof(feat[ALL_FEATURES], y, feat["provider_id"])
        model.train_final(feat[ALL_FEATURES], y)
        preds = model.predict(feat[ALL_FEATURES])
        assert len(preds) == len(feat)

    def test_oof_determinism(self):
        """Same data + same seed → identical OOF probabilities."""
        from vigilx.ml.claim_features_ml import build_claim_feature_matrix, ALL_FEATURES
        from vigilx.ml.claim_model import ClaimRiskModel, prepare_target

        feat = build_claim_feature_matrix(self.claims, self.providers, self.members)
        y = prepare_target(feat, self.gt)

        model1 = ClaimRiskModel(n_folds=3, random_state=42)
        probs1 = model1.fit_oof(feat[ALL_FEATURES], y, feat["provider_id"])

        model2 = ClaimRiskModel(n_folds=3, random_state=42)
        probs2 = model2.fit_oof(feat[ALL_FEATURES], y, feat["provider_id"])

        np.testing.assert_array_almost_equal(probs1, probs2, decimal=6,
                                              err_msg="OOF predictions are not deterministic")


# ------------------------------------------------------------------
# Output Schema Tests
# ------------------------------------------------------------------


class TestOutputSchema:
    def setup_method(self):
        self.claims = _make_small_claims(n=200, n_providers=20)
        self.providers = _make_small_providers(n=20)
        self.members = _make_small_members(n=50)
        self.gt = _make_gt_labels(self.claims, n_positive=10)

    def test_claim_ml_schema(self):
        """claim_ml output must contain required contract columns."""
        from vigilx.ml.claim_model import train_and_predict
        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, _, _ = train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )

        required_cols = {
            "claim_id", "provider_id",
            "ml_probability", "ml_risk_score", "ml_prediction",
            "oof_fold", "model_version", "feature_version",
            "prediction_timestamp",
        }
        for col in required_cols:
            assert col in claim_ml.columns, f"Missing required column: {col}"

    def test_claim_ml_row_count(self):
        from vigilx.ml.claim_model import train_and_predict
        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, _, _ = train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
        assert len(claim_ml) == len(self.claims)

    def test_claim_ml_probabilities_in_range(self):
        from vigilx.ml.claim_model import train_and_predict
        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, _, _ = train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
        assert claim_ml["ml_probability"].between(0.0, 1.0).all()

    def test_claim_ml_prediction_binary(self):
        from vigilx.ml.claim_model import train_and_predict
        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, _, _ = train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
        assert claim_ml["ml_prediction"].isin([0, 1]).all()

    def test_claim_ml_oof_fold_assigned(self):
        from vigilx.ml.claim_model import train_and_predict
        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, _, _ = train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
        assert (claim_ml["oof_fold"] > 0).all(), "Some claims have oof_fold=0 (unassigned)"
        assert claim_ml["oof_fold"].max() <= 3  # 3-fold

    def test_parquet_saved_to_disk(self):
        from vigilx.ml.claim_model import train_and_predict
        with tempfile.TemporaryDirectory() as tmpdir:
            train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
            parquet_path = Path(tmpdir) / "claim_ml.parquet"
            assert parquet_path.exists(), "claim_ml.parquet was not saved"

            # Verify it can be loaded
            loaded = pd.read_parquet(parquet_path)
            assert len(loaded) == len(self.claims)

    def test_model_artifacts_saved(self):
        from vigilx.ml.claim_model import train_and_predict, MODEL_VERSION
        with tempfile.TemporaryDirectory() as tmpdir:
            train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
            model_pkl = Path(tmpdir) / f"claim_model_v{MODEL_VERSION}.pkl"
            meta_json = Path(tmpdir) / "claim_model_metadata.json"
            assert model_pkl.exists(), "Model pickle not saved"
            assert meta_json.exists(), "Model metadata JSON not saved"

    def test_metadata_contains_required_fields(self):
        from vigilx.ml.claim_model import train_and_predict, MODEL_VERSION
        with tempfile.TemporaryDirectory() as tmpdir:
            train_and_predict(
                claims=self.claims,
                providers=self.providers,
                members=self.members,
                gt_claim_labels=self.gt,
                output_dir=tmpdir,
                n_folds=3,
            )
            with open(Path(tmpdir) / "claim_model_metadata.json") as f:
                meta = json.load(f)

        required_meta_fields = {
            "model_version", "feature_version", "saved_at",
            "n_folds", "features", "lgbm_params",
        }
        for field in required_meta_fields:
            assert field in meta, f"Missing metadata field: {field}"


# ------------------------------------------------------------------
# Evaluation Tests
# ------------------------------------------------------------------


class TestEvaluation:
    def test_precision_at_k(self):
        from vigilx.ml.evaluation import precision_at_k
        y = np.array([1, 0, 1, 0, 1, 0, 0, 0, 0, 0])
        score = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
        # Top 3: indices 0,1,2 → y=[1,0,1] → 2/3
        assert abs(precision_at_k(y, score, k=3) - 2 / 3) < 1e-9

    def test_recall_at_k(self):
        from vigilx.ml.evaluation import recall_at_k
        y = np.array([1, 0, 1, 0, 1, 0, 0, 0, 0, 0])
        score = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
        # 3 total positives. Top 5: indices 0,1,2,3,4 → y=[1,0,1,0,1] → 3 TPs → recall=3/3=1.0
        assert abs(recall_at_k(y, score, k=5) - 1.0) < 1e-9

    def test_compute_metrics_no_positives(self):
        from vigilx.ml.evaluation import compute_metrics
        y = np.zeros(100, dtype=int)
        score = np.random.rand(100)
        m = compute_metrics(y, score)
        assert m["roc_auc"] is None
        assert m["pr_auc"] is None

    def test_compute_metrics_with_positives(self):
        from vigilx.ml.evaluation import compute_metrics
        y = np.array([1] * 10 + [0] * 90)
        score = np.array([0.9] * 10 + [0.1] * 90)
        m = compute_metrics(y, score)
        assert m["roc_auc"] is not None
        assert m["roc_auc"] == 1.0  # perfect separation
        assert m["pr_auc"] == 1.0

    def test_evaluate_claim_model_produces_report(self):
        from vigilx.ml.claim_model import train_and_predict
        from vigilx.ml.evaluation import evaluate_claim_model

        claims = _make_small_claims(n=200, n_providers=20)
        providers = _make_small_providers(n=20)
        members = _make_small_members(n=50)
        gt = _make_gt_labels(claims, n_positive=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, model, fold_infos = train_and_predict(
                claims=claims, providers=providers, members=members,
                gt_claim_labels=gt, output_dir=tmpdir, n_folds=3,
            )
            report = evaluate_claim_model(
                claim_ml=claim_ml, claims=claims,
                gt_claim_labels=gt, fold_infos=fold_infos,
                output_dir=tmpdir,
            )

        assert "model" in report
        assert "baseline_amount" in report
        assert "n_claims" in report
        assert "n_providers" in report
        assert report["n_claims"] == len(claims)

    def test_evaluation_report_saved_to_disk(self):
        from vigilx.ml.claim_model import train_and_predict
        from vigilx.ml.evaluation import evaluate_claim_model

        claims = _make_small_claims(n=200, n_providers=20)
        providers = _make_small_providers(n=20)
        members = _make_small_members(n=50)
        gt = _make_gt_labels(claims, n_positive=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            claim_ml, model, fold_infos = train_and_predict(
                claims=claims, providers=providers, members=members,
                gt_claim_labels=gt, output_dir=tmpdir, n_folds=3,
            )
            evaluate_claim_model(
                claim_ml=claim_ml, claims=claims,
                gt_claim_labels=gt, fold_infos=fold_infos,
                output_dir=tmpdir,
            )
            report_path = Path(tmpdir) / "evaluation_report.json"
            assert report_path.exists()
