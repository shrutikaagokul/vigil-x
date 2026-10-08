# Vigil-X Backend Integration Contract & Schema Specification

**Document Version:** 1.0.0  
**Target Architecture:** Vigil-X / ClaimShield Nexus Monorepo  
**Audience:** Parallel Workstream Developers (ML/Risk, Detection, Network, Frontend)

---

## 1. Executive Summary & Ownership Boundaries

The Vigil-X system integrates multiple analytical pipelines into a high-performance, evidence-grounded Special Investigation Unit (SIU) platform. Because multiple engineers are developing in parallel, this document establishes **stable contract boundaries** between the analytical models and the SQLite database / FastAPI backend.

```
       Detection Outputs (R01–R10)
       Network Outputs (Louvain, Collusion Rings)
       ML / Risk Outputs (LightGBM, Isolation Forest, SIU Queue)
                         │
                         ▼
             Stable Analytical Contracts
                         │
                         ▼
                 SQLite (app.db)
                         │
                         ▼
                      FastAPI
                  ┌──────┴──────┐
                  ▼             ▼
          Investigator API   Evidence Packet
                                │
                                ▼
                              GenAI Narrator
                                │
                                ▼
                            Verifier
                                │
                                ▼
                     Verified Investigation Brief
```

### Workstream Ownership Matrix

| Workstream | Owner | Primary Responsibilities | Output Location / Contract |
| :--- | :--- | :--- | :--- |
| **Detection & Behavioral** | Workstream 2 | R01–R10 detection rules, temporal features, geographic checks | Emits `Alert` / `Evidence` records |
| **Network Intelligence** | Workstream 3 | Entity resolution, provider graph, Louvain communities | Emits `networks` DataFrame / records |
| **ML & Risk Intelligence** | Workstream 1 | LightGBM, calibration, SHAP, Isolation Forest, unified risk, case formation, SIU queue | Emits `cases`, `queue_items`, `risk_scores`, `claim_ml` |
| **Backend & GenAI** | Workstream 4 *(This work)* | SQLite schema, database loader, FastAPI endpoints, Evidence Packet builder, GenAI narration, deterministic verifier, Q&A | Consumes contracts, exposes `/api/*` |
| **Frontend** | Workstream 5 | React UI, Case view, Queue table, Graph visualization | Consumes `/api/*` |

> [!IMPORTANT]
> **Strict Ownership Boundary:** The backend does **NOT** invent or calculate LightGBM scores, anomaly scores, network risk, or SIU queue priorities in production. The backend validates, indexes, persists, packages, and serves them.

---

## 2. Real Mode vs. Fixture Mode (`DATA_MODE`)

Vigil-X operates under two explicit modes configured via the environment variable `VIGILX_DATA_MODE` (or `DATA_MODE`):

1. **`DATA_MODE=fixture` (Development Default):**
   - Unblocks frontend and API feature development while upstream ML and Risk models are being trained.
   - If upstream analytical outputs (`cases`, `queue_items`) are not supplied, the database loader derives deterministic development cases directly from detection alerts.
   - Every API response returns `"synthetic": true` and `"data_mode": "fixture"`.

2. **`DATA_MODE=real` (Production / Real Analytical Output Mode):**
   - Requires real analytical outputs produced by completed upstream workstreams.
   - **FAILS LOUDLY (`MissingAnalyticalOutputError`):** If upstream cases, queue, or risk score files are missing or incomplete, the loader raises an explicit error.
   - **Never silently fabricates risk scores or queue rankings.**
   - If `/api/queue` is requested in real mode before queue outputs are loaded, it returns HTTP 503 (`Queue data unavailable in REAL mode`).

---

## 3. Upstream Analytical Contracts

All analytical contracts are defined as Pydantic v2 models in `contracts/analytical.py`.

### Contract A: Alerts & Evidence (`AlertInput`, `EvidenceInput`)
Emitted by R01–R10 detection rules.

* **Alert Table:** `alerts`
  * `alert_id` (str, primary key, e.g. `"A-R01-abc123"`)
  * `rule_id` (str, pattern `^R(0[1-9]|10)$`, e.g. `"R01"`)
  * `rule_version` (str, default `"1.0.0"`)
  * `entity_type` (str, `"provider"`, `"member"`, or `"facility"`)
  * `entity_id` (str, non-empty, e.g. `"PRV0042"`)
  * `claim_ids` (List[str] or JSON array of string IDs)
  * `severity` (str: `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`)
  * `est_dollars` (float, `>= 0.0`)
  * `fp_notes` (str, optional false-positive considerations)
  * `metadata` (dict or JSON object)

* **Evidence Table:** `case_evidence`
  * `evidence_id` (str, primary key, e.g. `"E-R01-abc123-001"`)
  * `rule_id` (str, e.g. `"R01"`)
  * `claim_id` (str, optional primary claim link)
  * `plain_text` (str, factual human-readable finding)
  * `est_overpay` (float, `>= 0.0`)

---

### Contract B: Upstream Cases (`CaseInput`)
Emitted by the ML/Risk Case Builder.

* **Database Table:** `cases`
* **Schema & Types:**
  * `case_id` (str, primary key, non-empty, e.g. `"CASE-PRV-PRV0042"`)
  * `entity_type` (str, default `"provider"`)
  * `entity_id` (str, references provider or facility)
  * `entity_name` (str, human-readable name)
  * `status` (str, default `"NEW"`, allowed: `"NEW"`, `"IN_REVIEW"`, `"ACCEPTED"`, `"REJECTED"`, `"ESCALATED"`)
  * `priority` (str, `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`)
  * `risk_score` (float, range `[0.0, 100.0]`)
  * `confidence` (float, range `[0.0, 1.0]`, default `0.85`)
  * `evidence_strength` (float, range `[0.0, 1.0]`, default `0.80`)
  * `exposure_low` (float, `>= 0.0`)
  * `exposure_high` (float, `>= exposure_low`)
  * `members_affected` (int, `>= 0`)
  * `claims_count` (int, `>= 0`)
  * `why_flagged` (List[str] or JSON array)
  * `top_reasons` (List[str] or JSON array)
  * `benign_explanations` (List[str] or JSON array)
  * `risk_components` (Dict[str, float] with keys like `"rule_risk"`, `"network_risk"`, `"anomaly_risk"`)
  * `future_risk` (Dict[str, Any], optional velocity metrics)
  * `network_id` (str, optional network cluster ID)

* **Example Row:**
```json
{
  "case_id": "CASE-PRV-PRV0042",
  "entity_type": "provider",
  "entity_id": "PRV0042",
  "entity_name": "Metro Urgent Care",
  "status": "NEW",
  "priority": "HIGH",
  "risk_score": 78.5,
  "confidence": 0.88,
  "evidence_strength": 0.82,
  "exposure_low": 24000.0,
  "exposure_high": 31500.0,
  "members_affected": 45,
  "claims_count": 120,
  "why_flagged": ["Triggered R01 (Duplicate Billing)", "Triggered R06 (Impossible Timing)"],
  "top_reasons": ["Multiple identical billed claims within 24 hours", "Overlapping service durations"],
  "benign_explanations": ["Check for billing system resubmissions without modifier 77"],
  "risk_components": {"rule_risk": 0.75, "network_risk": 0.40, "anomaly_risk": 0.65},
  "future_risk": {"future_velocity_risk": 62.0},
  "network_id": "NET-003"
}
```

---

### Contract C: SIU Queue Items (`QueueItemInput`)
Emitted by the ML/Risk SIU Queue Builder.

* **Database Table:** `queue_items`
* **Schema & Types:**
  * `case_id` (str, primary key, references `cases.case_id`)
  * `rank` (int, `>= 1`, 1 = highest priority case)
  * `baseline_rank` (int, optional reference rank without ML re-ranking)
  * `entity_type` (str, `"provider"`, `"network"`, `"facility"`)
  * `entity_id` (str, non-empty)
  * `entity_name` (str, non-empty)
  * `risk` (float, range `[0.0, 100.0]`)
  * `priority` (str, `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`)
  * `exposure_low` (float, `>= 0.0`)
  * `exposure_high` (float, `>= exposure_low`)
  * `members_affected` (int, `>= 0`)
  * `severity` (str, `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`)
  * `evidence_strength` (float, range `[0.0, 1.0]`)
  * `confidence` (float, range `[0.0, 1.0]`)
  * `effort_hours` (float, `>= 0.1`, estimated investigator review hours)
  * `ev_per_hour` (float, `>= 0.0`, Expected Value dollar exposure recovered per review hour)
  * `slot` (int, `>= 1`)
  * `top_reasons` (List[str] or JSON array)

* **Example Row:**
```json
{
  "case_id": "CASE-PRV-PRV0042",
  "rank": 1,
  "baseline_rank": 3,
  "entity_type": "provider",
  "entity_id": "PRV0042",
  "entity_name": "Metro Urgent Care",
  "risk": 78.5,
  "priority": "HIGH",
  "exposure_low": 24000.0,
  "exposure_high": 31500.0,
  "members_affected": 45,
  "severity": "HIGH",
  "evidence_strength": 0.82,
  "confidence": 0.88,
  "effort_hours": 3.5,
  "ev_per_hour": 9000.0,
  "slot": 1,
  "top_reasons": ["Multiple identical billed claims", "Overlapping service times"]
}
```

---

### Contract D: Unified Risk Scores (`UnifiedRiskScoreInput`)
Emitted by the ML/Risk Calibration & Ensembling pipeline.

* **Database Table:** `risk_scores`
* **Primary Key:** `(entity_type, entity_id)`
* **Schema & Types:**
  * `entity_type` (str, default `"provider"`)
  * `entity_id` (str, non-empty)
  * `risk_score` (float, range `[0.0, 100.0]`)
  * `anomaly_score` (float, range `[0.0, 1.0]`)
  * `rule_score` (float, range `[0.0, 1.0]`)
  * `network_score` (float, range `[0.0, 1.0]`)
  * `future_risk_score` (float, range `[0.0, 1.0]`)
  * `confidence` (float, range `[0.0, 1.0]`)
  * `evidence_strength` (float, range `[0.0, 1.0]`)

---

### Contract E: Network Intelligence Features (`NetworkScoreInput`)
Emitted by the Network Intelligence workstream.

* **Database Table:** `networks`
* **Schema & Types:**
  * `network_id` (str, primary key, e.g. `"NET-001"`)
  * `community_id` (int, `>= 0`, Louvain cluster ID)
  * `n_providers` (int, `>= 1`, cluster size)
  * `hub_provider_id` (str, primary central provider)
  * `hard_link_score` (float, range `[0.0, 1.0]`)
  * `referral_score` (float, range `[0.0, 1.0]`)
  * `concentration_score` (float, range `[0.0, 1.0]`)
  * `ownership_score` (float, range `[0.0, 1.0]`)
  * `suspicious_claims` (int, `>= 0`)
  * `total_claims` (int, `>= 0`)
  * `total_exposure` (float, `>= 0.0`)
  * `triggered_rules` (str, comma-separated, e.g. `"R07,R09"`)
  * `hub_centrality` (float, range `[0.0, 1.0]`)
  * `documented_group` (int, `0` or `1`)
  * `network_feature_version` (str, default `"1.0.0"`)

---

### Contract F: Claim-Level ML Anomaly Scores (`ClaimMLScoreInput`)
Emitted by supervised/unsupervised claim scoring.

* **Database Table:** `claim_ml`
* **Schema & Types:**
  * `claim_id` (str, primary key, references `claims.claim_id`)
  * `anomaly_score` (float, range `[0.0, 1.0]`)
  * `ml_prediction` (str, optional model class label)
  * `model_version` (str, model run/version)

---

### Contract G: Pipeline Evaluation & Benchmarks (`EvaluationResultInput`)
Emitted by evaluation & ablation scripts.

* **Database Table:** `evaluation_results`
* **Schema & Types:**
  * `eval_id` (str, primary key, e.g. `"EVAL-001"`)
  * `eval_type` (str, e.g. `"pipeline_evaluation"`, `"ablation"`, `"ring_recovery"`)
  * `metrics` (Dict[str, Any], evaluation metrics dictionary)

---

## 4. Loader Ingestion Workflow

To load your workstream outputs into the SQLite database, you can pass pandas DataFrames or list-of-dicts directly into `db.loader.rebuild_database`:

```python
from db.loader import rebuild_database

rebuild_database(
    db_path="app.db",
    data_dict=synthetic_data_dict,       # providers, members, claims, etc.
    alerts=all_rule_alerts,             # Alert dataclass objects or dicts
    networks_df=network_features_df,     # Network intelligence records
    cases_data=upstream_cases,           # Validated against CaseInput
    case_evidence_data=upstream_evidence,# Validated against CaseEvidenceInput
    queue_data=upstream_queue,           # Validated against QueueItemInput
    risk_scores_data=upstream_risk,      # Validated against UnifiedRiskScoreInput
    claim_ml_data=upstream_claim_ml,     # Validated against ClaimMLScoreInput
    eval_results=evaluation_metrics,     # Benchmark dictionary
    data_mode="real",                    # or "fixture"
)
```

If any row fails Pydantic schema validation (e.g., negative exposure, out-of-range risk score, missing primary keys), an `AnalyticalValidationError` is raised immediately with the index and exact cause of the validation failure.

---

## 5. Verification Test Suite

Every analytical output should pass contract validation before being merged. You can run the dedicated contract test suite at any time:

```bash
pytest -v tests/test_contracts.py
```
