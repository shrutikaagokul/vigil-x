# Vigil-X: Claim & Utilization Intelligence Subsystem

Vigil-X is an AI-powered healthcare payer Fraud, Waste & Abuse (FWA) intelligence platform designed for Special Investigation Units (SIU). The system does **not** declare fraud; it identifies suspicious indicators, produces evidence-backed alerts, and prioritizes them for human investigation.

This subsystem provides the **Claim & Utilization Intelligence** foundation, implementing detection rules **R01 through R05**, shared feature engineering, and the common **Alert / Evidence data contract** for the entire platform.

---

## Architecture Overview

```
vigil-x/
├── src/
│   └── vigilx/
│       ├── __init__.py
│       ├── models/                  # Shared Alert/Evidence contract (Platform Source of Truth)
│       │   ├── __init__.py
│       │   └── alert.py             # Alert, Evidence, Severity dataclasses
│       ├── features/                # Shared vectorized feature engineering
│       │   ├── __init__.py
│       │   ├── claim_features.py    # Frequency, rolling 30d windows, E/M extraction
│       │   ├── member_features.py   # Member utilization, ghost member heuristics
│       │   ├── provider_features.py # E/M distributions, visit rates, unbundling rates
│       │   └── peer_features.py     # Median Absolute Deviation (MAD) z-scores, peer stats
│       ├── rules/                   # Detection rules
│       │   ├── __init__.py
│       │   ├── base.py              # BaseRule abstract class with config loader
│       │   ├── r01_duplicate_billing.py       # R01: Exact & near-duplicates
│       │   ├── r02_upcoding.py                # R02: E/M bell-curve & high-coding shifts
│       │   ├── r03_unbundling.py              # R03: Comprehensive + component pairs
│       │   ├── r04_phantom_services.py        # R04: Post-death, post-term, facility checks
│       │   └── r05_excessive_utilization.py   # R05: Rolling 30d caps & visit frequency
│       ├── runner.py                # RuleRunner & run_claim_utilization_rules API
│       └── data_loader.py           # Synthetic data loader with date parsing
├── config/
│   └── rules_config.yaml            # Centralized threshold & policy configuration
├── eval/
│   ├── __init__.py
│   └── evaluator.py                 # Precision/recall evaluation against ground truth
├── tests/                           # 52 unit & integration tests (89% coverage)
│   ├── test_alert_contract.py
│   ├── test_data_loader.py
│   ├── test_evaluator.py
│   ├── test_features.py
│   ├── test_r01_duplicate_billing.py
│   ├── test_r02_upcoding.py
│   ├── test_r03_unbundling.py
│   ├── test_r04_phantom_services.py
│   ├── test_r05_excessive_utilization.py
│   └── test_rule_runner.py
└── pyproject.toml
```

---

## Detection Rules (R01 – R05)

### R01 — Duplicate Billing
- **Exact Duplicates (`HIGH`)**: Identifies claims with identical `member_id`, `billing_provider_id`, `cpt_code`, `service_from`, and `allowed_amount`.
- **Near Duplicates (`MEDIUM`)**: Identifies claims with matching member, provider, CPT, and amount with service dates within $\pm 1$ day.
- **Legitimate Exclusions**: Automatically suppresses claims containing anatomical or repeat procedure modifiers (`LT`, `RT`, `50`, `76`, `77`) and claims with voided/corrected status (`voided`, `adjusted`, `replacement`).

### R02 — Upcoding Detection
- **Provider E/M Distribution Shift (`HIGH`)**: Computes provider Level 4/5 Evaluation & Management (E/M) share and compares against peer specialty groups using robust Median Absolute Deviation (MAD) z-scores. Flags providers with `MAD z-score > 3.0` and `Level 4/5 share >= 2.0x peer median`.
- **Claim-Level Evidence**: Attaches granular supporting evidence for Level-5 visits with low diagnostic complexity (`dx_complexity <= 1`) and abnormally short service durations below peer 25th percentile.

### R03 — Unbundling Detection
- **Comprehensive + Component Pairs (`MEDIUM`)**: Detects when a provider bills both comprehensive and component CPT codes on the same date for the same member without valid override modifiers (`59`, `25`, `XE`).
- **Provider-Level Escalation (`HIGH`)**: Automatically escalates to `HIGH` severity when a provider's overall unbundling rate exceeds the peer 95th percentile.

### R04 — Phantom Services Detection
- **Deceased Member Billing (`CRITICAL`)**: Claims with `service_from > death_date`.
- **Post-Termination Billing (`HIGH`)**: Claims with `service_from > termination_date` (or `enrollment_end`).
- **Inpatient Overlap (`HIGH`)**: Outpatient claims billed during a confirmed inpatient admission at a different facility.
- **Facility Status Checks (`HIGH` / `MEDIUM`)**: Claims billed before facility `open_date`, after `close_date`, or on days the facility does not operate.
- **Orphan Ambulance (`MEDIUM`)**: Ambulance transport claims (`A0xxx`) with no associated hospital or emergency claim within $\pm 1$ day.
- **Ghost Member Heuristic (`LOW`)**: Members with no historical claims for 12+ months presenting with 5+ claims with a single provider (weak signal, never triggers a case on its own).

### R05 — Excessive Utilization Detection
- **Member Rolling 30-Day Caps (`MEDIUM`)**: Enforces clinical rolling 30-day limits on sensitive procedure groups (e.g. max 12 physical therapy visits in any rolling 30-day window).
- **Provider Mean Visits (`HIGH`)**: Detects providers whose average visits per member exceeds $3.0\times$ the peer group median.

---

## Shared Alert / Evidence Contract

Every detection rule in Vigil-X conforms to the platform contract in [alert.py](file:///Users/shaktisaravananr07/Desktop/vigil-x/src/vigilx/models/alert.py):

```python
from vigilx.models.alert import Alert, Evidence, Severity

alert = Alert(
    alert_id=Alert.make_id(),
    rule_id="R01",
    rule_version="1.0",
    entity_type="provider",      # "provider", "member", or "facility"
    entity_id="PRV_12345",
    claim_ids=["C101", "C102"],
    severity=Severity.HIGH,      # LOW, MEDIUM, HIGH, CRITICAL
    est_dollars=450.00,
    evidence=[...],              # List of Evidence dataclasses
    fp_notes=["..."]
)
```

Each `Evidence` entry includes:
- `evidence_id`: Unique identifier (e.g., `E-R01-xxxx`)
- `rule_id` & `rule_version`
- `claim_ids`: Tracing IDs for SIU inspection
- `fields_matched`: Specific data columns triggering the rule
- `plain_text`: Human-readable explanation for investigator reports
- `est_overpay`: Estimated questionable dollars
- `severity`: Item severity
- `fp_notes`: Potential false positive considerations

---

## Integration Guide for Teammates (R06 – R10)

The subsystem is architected for zero-friction integration. Teammates implementing R06–R10 do not need to modify any existing rule code:

```python
from vigilx.rules.base import BaseRule
from vigilx.runner import create_full_runner
from vigilx.models.alert import Alert, Severity

class MyNetworkRule(BaseRule):
    rule_id = "R06"

    def detect(self, data: dict) -> list[Alert]:
        # Implement R06 detection logic
        return [...]

# Create runner pre-loaded with R01-R05 and register your rule
runner = create_full_runner()
runner.register(MyNetworkRule)

# Run full pipeline
data = {"claims": claims_df, "providers": providers_df}
alerts = runner.run(data)
```

---

## Testing & Verification

Run the complete test suite:

```bash
pytest -v
```

Run test suite with coverage report:

```bash
pytest --cov=vigilx --cov=eval --cov-report=term-missing
```

**Status:** 52 passing tests, **89% overall test coverage**.