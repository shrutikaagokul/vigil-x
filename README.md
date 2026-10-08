# Vigil-X: Network & Behavioral Intelligence Subsystem

Vigil-X is an AI-powered healthcare payer Fraud, Waste & Abuse (FWA) intelligence platform designed for Special Investigation Units (SIU). The system does **not** make legal determinations of fraud; instead, it detects behavioral and network anomalies, compiles evidence-backed alerts, reconstructs hidden entity relationships, and prioritizes cases for human investigators.

This subsystem provides the complete **Network & Behavioral Intelligence engine** (Rules R06–R10, graph construction, entity resolution, and temporal/geographic feature engineering).

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │ Raw Claims, Providers, Members, Facs    │
                      └────────────────────┬────────────────────┘
                                           │
                ┌──────────────────────────┴──────────────────────────┐
                ▼                                                     ▼
     ┌───────────────────────┐                             ┌───────────────────────┐
     │ Feature Engineering   │                             │   Entity Resolution   │
     │ - Haversine Distance  │                             │ - Address Clean & Norm│
     │ - Speed Checks (mph)  │                             │ - Fuzzy Owner Match   │
     │ - Weekly Panel / Spikes│                            │ - Bank / TIN Hashing  │
     │ - Rolling Baselines   │                             │ - Entity Clusters     │
     └──────────┬────────────┘                             └──────────┬────────────┘
                │                                                     │
                ├──────────────────────────┬──────────────────────────┤
                ▼                          ▼                          ▼
     ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
     │ Behavioral Rules     │   │ Graph & Network      │   │ Referral Intelligence│
     │ - R06: Timing        │   │ - Multi-Relational G │   │ - R07: Concentrations│
     │ - R08: Geo Anomaly   │   │ - Provider Projection│   │ - Reciprocal Loops   │
     │ - R10: Burst / Spike │   │ - Louvain Communities│   │ - Same-Day Lab Links │
     └──────────┬───────────┘   │ - R09: Identity Link │   └──────────┬───────────┘
                │               └──────────┬───────────┘              │
                │                          │                          │
                └──────────────────────────┼──────────────────────────┘
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │      Shared Alert & Evidence Layer      │
                      │       (contracts/alert.py)              │
                      └────────────────────┬────────────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
        ┌─────────────────────────┐                 ┌─────────────────────────┐
        │  SIU Investigation UI   │                 │ Risk & Case Aggregation │
        │  - Case Subgraphs       │                 │ - Rule alerts stream    │
        │  - Member Cohorts       │                 │ - Network risk signals  │
        └─────────────────────────┘                 └─────────────────────────┘
```

---

## Rules Owned (R06–R10)

| Rule ID | Name | Description | Key Triggers & Thresholds |
|---|---|---|---|
| **R06** | **Impossible Timing** | Flags impossible provider workload, superhuman travel between claims, and overlapping in-person services. | • Daily service minutes > 960 (16 hrs)<br>• Required travel speed > 60 mph between consecutive claims<br>• Overlapping in-person services for same member |
| **R07** | **Referral Anomaly** | Flags suspicious referral concentration, kickback loops, same-day high-cost lab referrals, and sudden referral volume spikes. | • >70% referrals directed to a single target (min 20 referrals)<br>• Reciprocal loops (A→B and B→A both ≥ 15)<br>• Same-day referral + high-cost lab claim<br>• 30-day referral volume > 3.0 z-score vs 90-day baseline |
| **R08** | **Geographic Anomaly** | Detects excessive member-provider travel distances, anomalous multi-county patient distributions, and suspicious facility addresses. | • Routine care distance > 75 miles (routine specialties)<br>• Non-routine specialty care > 150 miles or > specialty 99th percentile<br>• Provider billing patients across ≥ 5 counties<br>• Virtual office, residential, or PO Box facility billing |
| **R09** | **Shared Identity Link** | Uncovers hidden relationships between distinct billing providers using resolved entity clusters. | • Shared bank account hash (weight 1.0)<br>• Shared owner (exact 0.9, fuzzy ≥88% 0.7)<br>• Shared address suite (0.6) or building (0.4)<br>• Documented corporate group discount applied to prevent false positives |
| **R10** | **Burst / Spike** | Flags sudden anomalous surges in weekly billing volume compared to trailing historical baselines. | • Weekly paid amount > 3.0× trailing 12-week median<br>• Weekly dollar floor: ≥ $5,000<br>• Minimum history requirement: ≥ 4 weeks |

---

## Subsystem Structure

```
vigil-x/
├── config/
│   └── rules_config.yaml           # Centralized YAML configuration for R06-R10 thresholds
├── contracts/
│   └── alert.py                    # Shared Alert and Evidence dataclasses (common contract)
├── entity_resolution/
│   └── resolver.py                 # Address normalization, fuzzy matching, entity clustering
├── geo/
│   └── haversine.py                # Haversine distance and required travel speed calculators
├── temporal/
│   └── features.py                 # Weekly provider panels, rolling medians, daily summaries
├── network/
│   ├── graph_builder.py            # Multi-relational NetworkX graph builder
│   ├── provider_projection.py      # Weighted provider-to-provider projection
│   ├── community.py                # Louvain community detection & ring identification
│   ├── subgraph.py                 # Investigation case subgraph extractor with cohort bundling
│   └── network_features.py         # Tabular network risk signals table
├── rules/
│   ├── r06_timing.py               # R06 Impossible Timing implementation
│   ├── r07_referral.py             # R07 Referral Anomaly implementation
│   ├── r08_geographic.py           # R08 Geographic Anomaly implementation
│   ├── r09_identity.py             # R09 Shared Identity Link implementation
│   ├── r10_burst.py                # R10 Burst / Spike implementation
│   └── runner.py                   # Rule runner orchestrator for R06-R10 and all rules
├── generator/
│   └── synthetic_data.py           # Synthetic claims, providers, members, facilities generator
├── eval/
│   ├── evaluate.py                 # Ground truth evaluation & precision/recall metrics
│   └── ring_recovery.py            # Fraud ring community recovery measurement
└── tests/                          # 86 unit and end-to-end integration tests
```

---

## Teammate Integration Guide

### 1. For R01–R05 Rule Engineers
Your rules should import and return `Alert` and `Evidence` from `contracts.alert`:

```python
from contracts.alert import Alert, Evidence, Severity

# Inside your rule function:
evidence = Evidence(
    evidence_id=Evidence.generate_id("R01"),
    rule_id="R01",
    rule_version="1.0.0",
    claim_ids=["C1023", "C1024"],
    fields_matched=["procedure_code", "service_date", "member_id"],
    plain_text="Duplicate claims submitted for identical service on same date.",
    est_overpay=120.0,
    severity=Severity.HIGH.value,
    fp_notes="Check for bilateral procedure modifiers (RT/LT, 50).",
)

alert = Alert(
    alert_id=Alert.generate_id("R01"),
    rule_id="R01",
    rule_version="1.0.0",
    entity_type="provider",
    entity_id="PRV0042",
    claim_ids=["C1023", "C1024"],
    severity=Severity.HIGH.value,
    evidence=[evidence],
)
```
Add your rule functions to `rules/runner.py` inside `run_all_rules(data)`:
```python
# In rules/runner.py:
from rules.r01_duplicate import detect_duplicate_billing
alerts.extend(detect_duplicate_billing(data["claims"], config=config))
```

### 2. For Case & Risk Scoring Engineers
- Fetch all behavioral alerts via `run_network_behavior_rules(data)`.
- Compute the network-level risk features table:
```python
from network.network_features import compute_network_features

# P: provider projection graph, communities: Louvain clusters
df_networks = compute_network_features(P, communities, claims, alerts)
# Returns DataFrame with hard_link_score, referral_score, total_paid, hub_provider, etc.
```

### 3. For Frontend & SIU UI Engineers
To display the interactive case graph for an investigator inspecting provider `PRV0042`:
```python
from network.subgraph import get_case_subgraph

case_graph = get_case_subgraph(
    G=full_graph,
    entity_id="PRV0042",
    max_depth=2,
    max_member_nodes=5,  # bundles members beyond 5 into cohort nodes to prevent hairballs
)
# Returns JSON-serializable dict:
# {
#   "nodes": [{"id": ..., "type": "provider", "label": ...}],
#   "edges": [{"source": ..., "target": ..., "edge_type": "shared_bank_account", "weight": 1.0}],
#   "cohorts": [{"cohort_id": ..., "count": 28, "member_ids": [...]}],
#   "summary": {"total_nodes": 6, "total_edges": 8}
# }
```

---

## Running the System

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
pytest -v
```

### 3. Generate Synthetic Benchmark & Run Pipeline
```python
from generator.synthetic_data import generate_synthetic_data
from rules.runner import run_network_behavior_rules
from eval.evaluate import evaluate_rules

# Generate dataset with planted FWA fraud rings
data = generate_synthetic_data(n_providers=200, n_members=5000, n_facilities=30, n_months=12)

# Run detection
alerts = run_network_behavior_rules(data)

# Evaluate against ground truth (strictly isolated from detection)
metrics = evaluate_rules(
    alerts=alerts,
    gt_claim_labels=data["gt_claim_labels"],
    gt_entity_labels=data["gt_entity_labels"],
    gt_scenarios=data["gt_scenarios"],
)
print("Precision & Recall:", metrics)
```