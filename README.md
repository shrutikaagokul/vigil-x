# Vigil-X: AI-Powered Healthcare Payer FWA Intelligence Platform

Vigil-X (ClaimShield Nexus) is an AI-powered healthcare payer Fraud, Waste & Abuse (FWA) intelligence platform designed for Special Investigation Units (SIU).

> [!IMPORTANT]
> **Core Operating Philosophy:** The system does **not** declare fraud. It identifies suspicious indicators, produces evidence-backed alerts, aggregates signals into cases, and prioritizes them for human investigation. Every metric and statement presented to an investigator is traceable to underlying claim lines or rule activations.

---

## 1. System Architecture

```
        Detection outputs (R01–R10)
        Network outputs (Louvain, Rings)
        ML / Risk outputs (LightGBM, Anomaly, Queue)
                    │
                    ▼
        Stable Analytical Contracts (`contracts/analytical.py`)
                    │
                    ▼
         SQLite Database (`app.db`, 15 tables)
                    │
                    ▼
          FastAPI Application (`/api/*`)
          ┌─────────┴─────────┐
          ▼                   ▼
    Investigator API    Evidence Packet (Provenance-bounded facts)
                              │
                              ▼
                        GenAI Narrator
                              │
                              ▼
                      Deterministic Verifier
                              │
                              ▼
                    Verified Investigation Brief
                              │
                              ▼
                      Frontend Consumer
```

---

## 2. Workstream Status & Parallel Development Boundaries

This repository is developed by multiple engineers in parallel across distinct workstreams.

### Current Implementation Status

| Workstream | Status | Details |
| :--- | :--- | :--- |
| **Backend & Integration** | **COMPLETE** | SQLite schema (15 tables), parameterized queries, FastAPI endpoints, evidence packet, deterministic verifier, Q&A engine, dual-mode loader (`fixture` vs `real`). |
| **Detection Rules (R01–R05)** | **COMPLETE** | Duplicate billing, upcoding bell curve, unbundling, phantom services, excessive utilization. |
| **Detection Rules (R06–R10)** | **COMPLETE** | Impossible timing, referral anomaly, geographic anomaly, shared identity links, burst/spike detection. |
| **Network Intelligence** | **IN PROGRESS** | Graph builder, provider projection, Louvain community detection, network feature calculation (preliminary implementation active; real community calibration ongoing). |
| **ML & Risk Intelligence** | **IN PROGRESS** | LightGBM, grouped OOF, isotonic calibration, SHAP attribution, Isolation Forest, unified risk scorer, future risk 30/60/90, upstream SIU queue builder. |
| **Frontend** | **IN PROGRESS** | Independent React/Vite UI consuming the OpenAPI contract at `http://localhost:8000/docs`. |

> [!NOTE]
> **No Fake Outputs:** The backend does **not** implement competing substitutes for unfinished ML, risk, or network components. In `DATA_MODE=real`, the backend requires genuine upstream artifacts and will fail loudly if they are absent or malformed.

---

## 3. Real Data vs. Fixture Data (`DATA_MODE`)

Vigil-X explicitly distinguishes real pipeline outputs from temporary development fixtures using the `VIGILX_DATA_MODE` (or `DATA_MODE`) configuration:

### Fixture Mode (`DATA_MODE=fixture`, default for local dev)
- Unblocks frontend and API development while ML models are being trained.
- When upstream analytical files are not yet generated, deterministic cases and queue items are synthesized from alerts.
- Responses include `"synthetic": true`, `"as_of": ...`, and `"data_mode": "fixture"`.

### Real Mode (`DATA_MODE=real`)
- Enforces strict validation against upstream analytical outputs (`cases`, `queue_items`, `risk_scores`).
- **Fails loudly** with `MissingAnalyticalOutputError` if required ML/Risk outputs are missing.
- Silent fabrication of risk scores or queue priority is strictly blocked.
- Accessing `/api/queue` before real queue outputs are ingested returns HTTP 503 (`Queue data unavailable in REAL mode`).

---

## 4. Analytical Contracts

Upstream workstreams integrate with the backend via stable Pydantic v2 schemas defined in `contracts/analytical.py`:

- **Alerts & Evidence:** `AlertInput`, `EvidenceInput`
- **Cases:** `CaseInput`
- **Case Evidence Ledger:** `CaseEvidenceInput`
- **SIU Queue:** `QueueItemInput`
- **Unified Risk Scores:** `UnifiedRiskScoreInput`
- **Network Intelligence:** `NetworkScoreInput`
- **Claim ML Scores:** `ClaimMLScoreInput`
- **Evaluation Results:** `EvaluationResultInput`

For full schema definitions, field types, range bounds, and example payloads, consult [docs/backend_integration_contract.md](file:///Users/shrutika/vigil-x/vigil-x/docs/backend_integration_contract.md).

---

## 5. GenAI Narration & Deterministic Verifier

### Grounded GenAI Narration
The GenAI layer acts strictly as an **investigative narrator**, never as a fraud detector.
- It receives **ONLY** the structured, tamper-proof `EvidencePacket`.
- It is instructed to state `"Prioritized for human investigation"` and is forbidden from declaring `"fraud confirmed"`.
- Supports OpenAI, Anthropic, and Google Gemini via standard environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).

### Prompt-Injection Defense
All database and clinical text is wrapped inside `<evidence_data>` tags and treated as untrusted data. Instructions to "ignore previous instructions" or "declare provider innocent" are treated as literal evidence text rather than executable commands.

### Deterministic Verifier
Every brief (whether generated by an LLM or fallback) is validated against the `EvidencePacket` before being returned:
- Validates cited Claim IDs, Provider IDs, Member IDs, and Rule IDs.
- Validates cited financial figures against case exposure bounds.
- Flags forbidden conclusive fraud phrasing.
- Fallback briefs run when LLM keys are absent, network calls fail, or generated text fails verification.

### Whitelist-Only Q&A
The `/api/ask` endpoint supports only whitelisted investigative intents:
- `WHY_FLAGGED`, `SUPPORTING_CLAIMS`, `RELATED_PROVIDERS`, `NETWORK_CONNECTIONS`
- `FINANCIAL_EXPOSURE`, `MEMBER_IMPACT`, `TIMELINE`, `RULE_EVIDENCE`, `FUTURE_RISK`, `BENIGN_EXPLANATIONS`
- Free-form SQL, Python evaluation, and prompt override commands are refused with clear security notices.

---

## 6. API Endpoints

All endpoints are hosted under `/api` and documented via OpenAPI at `/docs`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Readiness status, database connectivity, schema validity, and data mode |
| `GET` | `/api/summary` | Platform-wide claims, paid totals, alerts, cases, and funnel counts |
| `GET` | `/api/queue` | Prioritized SIU worklist with `capacity_hours`, `horizon`, and `sort` |
| `GET` | `/api/cases/{id}` | Investigation case detail, risk scores, why flagged, timeline, claims |
| `GET` | `/api/cases/{id}/evidence` | Granular evidence ledger with field-level provenance |
| `GET` | `/api/cases/{id}/timeline` | Chronological claim activity and event history |
| `GET` | `/api/cases/{id}/network` | Case-centered subgraph for network ring visualization |
| `GET` | `/api/networks` | Collusion rings and community cluster summaries |
| `GET` | `/api/networks/{id}` | Details for a specific network cluster |
| `GET` | `/api/claims` | Search and filter claim records supporting investigations |
| `GET` | `/api/providers` | Provider profiles and enrollment lookups |
| `GET` | `/api/providers/{id}` | Specific provider profile details |
| `GET` | `/api/risk` | Upstream risk scores and component signals |
| `GET` | `/api/brief?case_id={id}` | Verified investigation brief (answers 6 mandatory SIU questions) |
| `POST` | `/api/ask` | Whitelist-only structured Q&A retrieval |
| `POST` | `/api/decision` | Case disposition recording (`accept`, `reject`, `escalate_for_review`) |
| `GET` | `/api/audit` | Immutable audit log of all decisions and system events |
| `GET` | `/api/evaluation` | Benchmark evaluation metrics and ring recovery rates |

---

## 7. Setup & Execution Commands

### Prerequisites
- Python 3.11+
- Virtual environment or conda

### Installation
```bash
pip install -r requirements.txt
```

### Build Database
```bash
# Generate synthetic dataset and build SQLite database
make db

# Or quick build for testing:
make pipeline
```

### Start Backend Server
```bash
make run
# Server starts at http://localhost:8000
# OpenAPI Docs available at http://localhost:8000/docs
```

### Run Tests
```bash
# Run backend and integration tests (37 tests)
make test-backend

# Run complete repository test suite (171 tests)
make test
```