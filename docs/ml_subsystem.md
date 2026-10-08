# Vigil-X: Machine Learning & Risk Intelligence Subsystem

The **Vigil-X ML Subsystem** delivers an end-to-end, multi-tier intelligence pipeline for Special Investigation Units (SIU) in healthcare payer Fraud, Waste & Abuse (FWA) detection.

Unlike heuristic rules that detect isolated deterministic patterns, the ML subsystem identifies subtle multi-dimensional signals, calibrates posterior probabilities, generates provable Shapley attributions, detects anomalous provider billing behavior, and forecasts forward risk across 30, 60, and 90-day horizons.

---

## 1. Subsystem Architecture

```
                                 Raw Claims Data
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │  Claim Features │       │Provider Feature │       │ Multi-Snapshot  │
    │ (Leakage-Free)  │       │ Behavioral Set  │       │ Target Windows  │
    └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
             │                         │                         │
             ▼                         ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │ LightGBM Model  │       │Isolation Forest │       │ Future Risk     │
    │ Provider-Grouped│       │ Provider Anomaly│       │ LightGBM 30/60/ │
    │     5-Fold OOF  │       │  Unsupervised   │       │  90-Day Models  │
    └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
             │                         │                         │
      ┌──────┴──────┐                  │                         │
      ▼             ▼                  │                         │
┌───────────┐ ┌───────────┐            │                         │
│ Isotonic  │ │ TreeSHAP  │            │                         │
│Calibration│ │Attribution│            │                         │
└─────┬─────┘ └─────┬─────┘            │                         │
      └──────┬──────┘                  │                         │
             ▼                         ▼                         ▼
     claim_ml.parquet       provider_anomaly.parquet    future_risk.parquet
  (Calibrated prob + SHAP)    (Anomaly percentile)     (Forward horizon risk)
             │                         │                         │
             └─────────────────────────┼─────────────────────────┘
                                       ▼
                         Unified Risk Engine (Downstream)
```

---

## 2. Component Specifications

### 2.1 Claim-Level LightGBM (`src/vigilx/ml/claim_model.py`)
- **Objective**: Classify individual suspicious claims in an extreme class imbalance setting (~0.3% positive).
- **Cross-Validation**: 5-Fold `StratifiedGroupKFold` grouped strictly by `provider_id`.
  - **Leakage Prevention**: All claims for any given provider reside strictly within one fold. No provider crosses train/validation boundaries.
  - **Class Weighting**: `is_unbalance=True` dynamically scales gradient weights by `neg_count / pos_count`.
- **Feature Matrix** (`src/vigilx/ml/claim_features_ml.py`):
  - 25 Numeric Features + 3 Categorical Features (`pos_code`, `claim_type`, `provider_specialty`).
  - Raw identifiers (`claim_id`, `member_id`, `provider_id`, `facility_id`), post-hoc billing timestamps, and ground truth labels are strictly excluded.

### 2.2 Isotonic Probability Calibration (`src/vigilx/ml/calibration.py`)
- **Philosophy**: Tree models optimized under `is_unbalance=True` produce raw probabilities that reflect monotonic risk rankings, but overestimate absolute posterior probabilities.
- **Strict OOF Fitting**:
  - Calibrators are **never** fitted on in-sample training data.
  - For validation fold $k$, the calibrator is fitted solely on out-of-fold predictions from folds $j \neq k$.
  - Final inference calibrator is fitted on the full provider-grouped OOF prediction set.
- **Robustness**: Includes sample size ($\ge 50$), minimum positive count ($\ge 5$), and multi-class checks with safe fallback clipping to prevent degenerate transforms.
- **Evaluation**: Brier score loss, Expected Calibration Error (ECE, 10-bin equal width), Log Loss, and reliability curve binning.

### 2.3 TreeSHAP Explainability (`src/vigilx/ml/explainability.py`)
- **Native TreeSHAP**: Evaluated directly through LightGBM's optimized C++ engine (`pred_contrib=True`).
- **Mathematical Guarantee**: Local accuracy holds — Shapley values sum exactly to the log-odds margin offset from baseline:
  $$\sum_{i=1}^M \phi_i(x) + \phi_0 = f(x) = \ln\left(\frac{p}{1-p}\right)$$
- **Attribution Contract**:
  - `top_features`: JSON-serialized dictionary of top positive risk drivers and signed values.
  - `top_feature_1`, `top_feature_1_shap`: Primary risk driver.
  - `top_feature_2`, `top_feature_2_shap`: Secondary risk driver.
  - `top_feature_3`, `top_feature_3_shap`: Tertiary risk driver.
- **Human-Readable Output** (`format_claim_explanation`): Formats clean summaries for SIU investigators.

### 2.4 Isolation Forest Provider Anomaly Detection (`src/vigilx/ml/provider_anomaly.py`)
- **Concept**: Identifies providers exhibiting statistically anomalous macro billing behavior compared to peer norms.
- **Unsupervised**: Ground truth labels are **never** fed into features or model fitting.
- **Behavioral Profiling** (`src/vigilx/ml/provider_features_ml.py`):
  - Claim volume, financial totals, member counts, visits per member.
  - High-acuity E/M share (levels 4–5 vs 1–3).
  - Out-of-hours billing share (weekends, off-peak).
  - Rapid claim velocity bursts (max 7-day to 30-day ratios).
  - Distinct CPT / diagnosis breadth and travel distances.
- **Scaling**: `RobustScaler` (median & IQR) prevents outlier distortion.
- **Output Schema**:
  - `anomaly_score`: Raw decision score (higher = more anomalous).
  - `anomaly_percentile`: Percentile rank $[0, 100]$.
  - `anomaly_flag`: Binary flag at configured contamination ($\alpha = 0.05$).

### 2.5 Future Risk Forecasting (`src/vigilx/ml/future_risk.py`)
- **Objective**: Forecast the probability that a provider will be implicated in suspicious billing within a forward window of 30, 60, or 90 days.
- **Multi-Snapshot Panel**:
  - Historical snapshots spaced at least 30 days apart.
  - **Temporal Integrity**: Features are extracted strictly as-of `snapshot_date`.
  - Targets are computed strictly from claims occurring within $(t_{\text{snapshot}}, t_{\text{snapshot}} + \Delta t]$.
- **Models**: Independent LightGBM classifiers trained per horizon ($30\text{d}, 60\text{d}, 90\text{d}$).
- **Output**: `risk_30d`, `risk_60d`, `risk_90d` for every active provider.

### 2.6 Feature Group Ablation Study (`src/vigilx/ml/ablation.py`)
Systematically isolates the marginal utility of each feature domain by retraining on identical provider splits:
1. `full_model`: All 28 features (Reference).
2. `no_temporal`: Ablates rolling 7d/30d/90d claim counts and dollars.
3. `no_provider_util`: Ablates provider volume, member reach, and E/M acuity share.
4. `no_member_util`: Ablates member claim volume, provider shopping count, and CPT breadth.
5. `no_geo`: Ablates patient-provider distance.
6. `claim_base_only`: Removes all historical/behavioral features, retaining only claim-level attributes.

Reports $\Delta\text{PR-AUC}$, $\Delta\text{ROC-AUC}$, Precision@50, and Rank-Lift@50 against the full model.

---

## 3. Data Contracts & Output Schemas

### `claim_ml.parquet`
| Field | Type | Description |
|---|---|---|
| `claim_id` | `str` | Claim identifier |
| `provider_id` | `str` | Provider identifier |
| `ml_risk_score` | `float32` | Raw LightGBM model score |
| `ml_probability` | `float32` | Raw probability score |
| `calibrated_probability` | `float32` | Isotonic calibrated probability |
| `ml_prediction` | `int8` | Binary flag ($\ge 0.5$ calibrated threshold) |
| `oof_fold` | `int16` | Validation fold assignment ($1 \dots K$) |
| `top_features` | `str (JSON)` | Top risk driver dictionary |
| `top_feature_1` | `str` | Primary risk driver feature name |
| `top_feature_1_shap` | `float32` | Signed Shapley contribution for #1 |
| `top_feature_2` | `str` | Secondary risk driver feature name |
| `top_feature_2_shap` | `float32` | Signed Shapley contribution for #2 |
| `top_feature_3` | `str` | Tertiary risk driver feature name |
| `top_feature_3_shap` | `float32` | Signed Shapley contribution for #3 |
| `model_version` | `str` | Model version tag (`1.0.0`) |
| `feature_version` | `str` | Feature set version tag (`1.0.0`) |
| `prediction_timestamp` | `str` | ISO 8601 UTC timestamp |

### `provider_anomaly.parquet`
| Field | Type | Description |
|---|---|---|
| `provider_id` | `str` | Provider identifier |
| `anomaly_score` | `float32` | Isolation Forest anomaly score (higher = unusual) |
| `anomaly_percentile` | `float32` | Percentile rank $[0, 100]$ |
| `anomaly_flag` | `int8` | Binary flag ($1$ if in top 5% anomalous) |
| `model_version` | `str` | Anomaly detector version |
| `feature_version` | `str` | Behavioral feature version |
| `scored_at` | `str` | ISO 8601 UTC timestamp |

### `future_risk.parquet`
| Field | Type | Description |
|---|---|---|
| `provider_id` | `str` | Provider identifier |
| `risk_30d` | `float32` | 30-day forward risk probability |
| `risk_60d` | `float32` | 60-day forward risk probability |
| `risk_90d` | `float32` | 90-day forward risk probability |
| `prediction_date` | `str` | Cutoff date for features (ISO YYYY-MM-DD) |
| `model_version` | `str` | Future risk model version |
| `feature_version` | `str` | Behavioral feature version |
| `scored_at` | `str` | ISO 8601 UTC timestamp |

---

## 4. Evaluation & Scientific Integrity Guarantees

1. **No Target Leakage**:
   - Ground truth labels are strictly isolated from feature engineering.
   - Identifier columns (`claim_id`, `member_id`, `provider_id`) are never passed as training features.
2. **Strict Grouped OOF**:
   - Provider-level grouping ensures models are tested exclusively on held-out providers.
   - Calibration curves are constructed strictly out-of-fold.
3. **Temporal Realism**:
   - All behavioral and future risk aggregations respect `snapshot_date` cutoffs.
   - No future claims or events pollute feature tables.
4. **Rank-Lift Over Baselines**:
   - Evaluated against standard industry baselines:
     - **Baseline 0 (Random)**: Lower bound expected performance.
     - **Baseline 1 (Amount-Only)**: Simple heuristic ranking by `paid_amount`.
   - The ML model demonstrates marked rank lift across Precision@K and Recall@K.

---

## 5. Verification & Test Suite

The subsystem is fully verified via unit, integration, and contract tests:
```bash
# Run complete test suite (228 tests)
pytest

# Run Phase 1 ML tests (45 tests)
pytest tests/test_ml_phase1.py -v

# Run Phase 2 ML tests (49 tests)
pytest tests/test_ml_phase2.py -v
```

All 228 test cases pass with zero regressions across the codebase.
