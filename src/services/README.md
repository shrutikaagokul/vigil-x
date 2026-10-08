# ClaimShield Nexus — Service Layer & Mock/Live Architecture

This directory provides the centralized data abstraction and typed API client for the ClaimShield Nexus / Vigil-X frontend.

---

## 1. Mock / Live Architecture

All API calls from the application are routed through domain services (`src/services/*Service.ts`). Pages, hooks, and UI components **never** fetch backend endpoints directly and do not inspect environment flags.

```
React Component / Hook / TanStack Query
                  │
                  ▼
         Domain Service Module
        (e.g., caseService.ts)
                  │
                  ▼
         isMockMode() check
        ┌─────────┴─────────┐
        ▼                   ▼
  Mock Fixtures        Live API Client
(src/services/mockData)  (fetch -> VITE_API_BASE_URL)
```

---

## 2. API Mode Selection

API mode is configured via environment variables:

- **Mock Mode (Default for offline development & benchmarks)**:
  ```env
  VITE_API_MODE=mock
  ```
- **Live Mode (Connected to FastAPI / backend server)**:
  ```env
  VITE_API_MODE=live
  VITE_API_BASE_URL=http://localhost:8000
  ```

---

## 3. Fixture & Endpoint Mapping

| Canonical Endpoint | Service Function | Mock Source |
|---|---|---|
| `GET /api/summary` | `getSummary()` | `mockData/summary.ts` |
| `GET /api/queue?...` | `getQueue(params)` | `mockData/queue.ts` (`calculateMockQueue`) |
| `GET /api/cases/{id}` | `getCase(id)` | `mockData/cases.ts` |
| `GET /api/cases/{id}/evidence` | `getCaseEvidence(id)` | `mockData/evidence.ts` |
| `GET /api/cases/{id}/timeline` | `getCaseTimeline(id)` | `mockData/timeline.ts` |
| `GET /api/cases/{id}/network` | `getCaseNetwork(id)` | `mockData/networks.ts` |
| `GET /api/networks/{id}` | `getNetwork(id)` | `mockData/networks.ts` |
| `GET /api/claims/{id}` | `getClaim(id)` | `mockData/claims.ts` |
| `GET /api/providers/{id}` | `getProvider(id)` | `mockData/providers.ts` |
| `GET /api/risk/{id}?horizon=` | `getRisk(id, horizon)` | `mockData/risk.ts` |
| `POST /api/cases/{id}/brief` | `generateBrief(id)` | `caseService.ts` |
| `POST /api/cases/{id}/ask` | `askCase(id, question)` | `caseService.ts` |
| `POST /api/cases/{id}/decision` | `submitDecision(id, req)` | `caseService.ts` |
| `GET /api/audit` | `getAudit()` | `mockData/audit.ts` |
| `GET /api/evaluation` | `getEvaluation()` | `mockData/evaluation.ts` |
| `GET /api/health` | `getHealth()` | `mockData/health.ts` |
| `POST /api/ingest/batch` | `startIngest(req)` | `mockData/ingest.ts` |
| `GET /api/ingest/{run_id}` | `getIngestRun(runId)` | `mockData/ingest.ts` |
| `POST /api/ingest/reset` | `resetIngest()` | `ingestService.ts` |

---

## 4. Contract Status: Confirmed vs. Provisional

### Confirmed from Backend Contracts
- `Evidence` schema (`evidence_id`, `rule_id`, `rule_version`, `claim_ids`, `fields_matched`, `plain_text`, `est_overpay`, `severity`, `fp_notes`) is directly derived from `contracts/alert.py`.
- `Alert` schema (`alert_id`, `rule_id`, `rule_version`, `entity_type`, `entity_id`, `claim_ids`, `severity`, `est_dollars`, `evidence`, `fp_notes`, `metadata`) is directly derived from `contracts/alert.py`.
- `Network` graph and `NetworkCohort` schema (`nodes`, `edges`, `cohorts`, `summary` with `n_nodes`, `n_edges`, `n_cohorts`, `total_members`) is derived from `network/subgraph.py`.
- `Claim` and `Provider` schemas match the tables in `schema.sql`.

### Provisional Frontend Shapes (Subject to Backend REST Finalization)
- `QueueResponse` wrapper with `capacity_summary` and `capacity_settings`.
- `CaseBrief` and `AskResponse` response payload structure for the AI Copilot endpoint.
- `DecisionResponse` response schema for recorded SIU investigator decisions.
- `EvaluationSummary` structured summary aggregating `eval/evaluate.py` metrics.

---

## 5. How to Switch to Live Mode

1. In `.env.local`, set:
   ```env
   VITE_API_MODE=live
   VITE_API_BASE_URL=http://localhost:8000
   ```
2. Restart the Vite dev server (`npm run dev`).
3. If the backend server is reachable, all requests will execute HTTP calls via `fetch` to `http://localhost:8000/api/*`.
