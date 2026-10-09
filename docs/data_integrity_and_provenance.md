# VIGILX — Data Integrity, Currency & Artifact Provenance Architecture

## 1. Currency Specification & Consistency Audit

### 1.1 Empirical Audit Findings
A comprehensive inspection across the entire repository confirmed that monetary amounts represent **United States Dollars (USD / $)**:

1. **Synthetic Data Generator (`generator/synthetic_data.py`)**:
   - Generates medical procedure claims using standard US CMS CPT-4 codes (`CPT99213`, `CPT99214`, `CPT99215`, `CPT80053`) and ICD-9/10 diagnostic codes (`ICD001`–`ICD999`).
   - Places of service are standard CMS POS codes (`11` = Office, `22` = On Campus-Outpatient Hospital, `23` = Emergency Room).
   - Geographic locations are US counties (`Adams`, `Baker`, `Douglas`, `Lincoln`), US cities, and US coordinates (e.g. lat 33.0 / long -84.0).
   - Monetary reimbursement values follow log-normal distribution with median ~$90. Office visits are priced at $150–$200, outpatient lab panels at $500, complex evaluations at $800. These align directly with standard US Medicare and commercial insurer fee schedules.

2. **Detection Rules (`rules/` & `src/vigilx/rules/`)**:
   - Every rule template and evidence plain-text string formats amounts with `$`:
     - `rules/r10_burst.py`: `f"Provider {pid} paid ${current:,.2f}... trailing {trailing_weeks}-week median of ${median:,.2f}. Dollar floor: ${dollar_floor:,}."`
     - `rules/r01_duplicate_billing.py`: `f"... amount=${amount:,.2f}."`
     - `src/vigilx/detection/rules/r10_billing_bursts.py`: `f"Billing Burst: Provider billed ${amt:,.2f}... over the ${historical_weekly_avg:,.2f} baseline."`
   - Config thresholds explicitly declare `dollar_floor: 5000` ($5,000).

3. **Contracts, Configurations, & Outputs**:
   - `contracts/analytical.py`: `est_dollars: float = Field(..., description="Estimated dollar amount associated with alert")`.
   - `risk/risk_config.yaml`: `estimated_rule_dollars` weight, `dollars_cap: 50000.0`.
   - `siu/siu_config.yaml`: `exposure_norm_cap: 50000.0`.
   - `siu/capacity_optimizer.py`: CLI explicitly logs `Exposure: ${top1['estimated_exposure']:,.2f}`.
   - `src/types/queue.ts`: Interface defines `readonly est_dollars: number;`.

4. **Root Cause of Frontend INR Appearance**:
   - The UI team in India utilized a presentation-layer utility (`src/utils/currency.ts` `formatINR`) for visual mockup without modifying the underlying numbers.
   - In accordance with the project constraints, **monetary values are never silently converted or scaled**. Doing so would distort risk thresholds, dollar caps, and ML features.
   - The backend contracts (`CaseHeader`, `CaseDetail`, `CaseEvidenceItem`, `QueueItem`, `SummaryResponse`) and endpoints now explicitly specify `currency: "USD"` across all contracts, matching the data and rule evidence.

---

## 2. Dataset Versions & Artifact Provenance

Vigil-X maintains two cleanly separated and reproducible dataset tiers:

### 2.1 Benchmark / Full Research Dataset
- **Scale**: 150,345 claims, 1,200 providers, 25,000 members, 110 facilities across 24 months.
- **Purpose**: Offline training of ML models (isolation forests, claim-level lightgbm, temporal forecasting) and ground-truth benchmark evaluation.
- **Storage**:
  - Raw / Synthetic Data: `data/*.parquet`
  - ML Phase 1 Models & Scores: `outputs/phase1/` (`claim_ml.parquet`, `claim_model_v1.0.0.pkl`)
  - ML Phase 2 Models & Scores: `outputs/phase2/` (`provider_anomaly.parquet`, `future_risk.parquet`, `future_risk_*_model.pkl`)
  - Unified Risk Scores: `outputs/risk/` (`provider_scores.parquet`, 1,200 rows)
  - Full Cases: `outputs/cases/` (`cases.parquet`, 172 cases)
  - Full SIU Queue: `outputs/siu/` (`siu_queue.parquet`, 172 queue items)
  - Full Evaluation Reports: `outputs/siu/siu_evaluation_report.json`, `outputs/risk/risk_evaluation_report.json`
- **Execution Script**:
  - `python3 generator/synthetic_data.py` (writes to `data/`)
  - `python3 src/vigilx/ml/pipeline.py`
  - `python3 risk/unified_risk.py`
  - `python3 cases/case_builder.py`
  - `python3 siu/capacity_optimizer.py`

### 2.2 Quick Demo Dataset (Authoritative for Live UI / API)
- **Scale**: 5,345 claims, 80 providers, 1,500 members, 15 facilities, 176 alerts, 80 cases.
- **Purpose**: Ultra-fast end-to-end demo execution (< 10 seconds), deterministic live UI exploration, instant test suite validation.
- **Storage**:
  - SQLite Application Database: `app.db` (Primary source for FastAPI `api/main.py`)
  - Exported Compatible Parquet Artifacts: `outputs/quick/` (`cases.parquet`, `siu_queue.parquet`, `case_evidence.parquet`, `provider_scores.parquet`, `evaluation_report.json`)
- **Execution Script**:
  ```bash
  python3 scripts/build_db.py --quick
  ```

---

## 3. Demo Run Workflow

To run the complete Vigil-X application cleanly from scratch:

```bash
# 1. Build the authoritative application database and quick artifacts
python3 scripts/build_db.py --quick

# 2. Run backend test suite
python3 -m pytest tests/

# 3. Validate all 16 API endpoints
python3 scripts/validate_endpoints.py

# 4. Start the FastAPI backend
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 5. Start the frontend (in a separate terminal)
npm run dev
```
