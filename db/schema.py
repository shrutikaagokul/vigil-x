"""
SQLite schema definitions and initialization for Vigil-X.
"""
from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
-- ── Core Domain Tables ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS providers (
    provider_id       TEXT PRIMARY KEY,
    npi               TEXT,
    name              TEXT,
    specialty         TEXT,
    latitude          REAL,
    longitude         REAL,
    address           TEXT,
    suite             TEXT,
    city              TEXT,
    state             TEXT,
    zip               TEXT,
    county            TEXT,
    facility_type     TEXT,
    owner_name        TEXT,
    owner_entity      TEXT,
    registered_agent  TEXT,
    bank_hash         TEXT,
    tin_hash          TEXT,
    group_id          TEXT,
    enrolled_date     TEXT
);

CREATE TABLE IF NOT EXISTS members (
    member_id         TEXT PRIMARY KEY,
    name              TEXT,
    dob               TEXT,
    gender            TEXT,
    latitude          REAL,
    longitude         REAL,
    address           TEXT,
    city              TEXT,
    state             TEXT,
    zip               TEXT,
    county            TEXT,
    plan_type         TEXT,
    enrolled_date     TEXT
);

CREATE TABLE IF NOT EXISTS facilities (
    facility_id       TEXT PRIMARY KEY,
    name              TEXT,
    facility_type     TEXT,
    latitude          REAL,
    longitude         REAL,
    address           TEXT,
    suite             TEXT,
    city              TEXT,
    state             TEXT,
    zip               TEXT,
    county            TEXT,
    owner_name        TEXT,
    owner_entity      TEXT,
    capacity          INTEGER
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id              TEXT PRIMARY KEY,
    member_id             TEXT,
    provider_id           TEXT,
    facility_id           TEXT,
    referring_provider_id TEXT,
    service_date          TEXT,
    service_start_ts      TEXT,
    service_end_ts        TEXT,
    service_minutes       REAL,
    pos_code              TEXT,
    procedure_code        TEXT,
    diagnosis_code        TEXT,
    paid_amount           REAL DEFAULT 0.0,
    billed_amount         REAL DEFAULT 0.0,
    allowed_amount        REAL DEFAULT 0.0,
    status                TEXT,
    claim_type            TEXT,
    modifier              TEXT
);

CREATE TABLE IF NOT EXISTS claim_lines (
    line_id           TEXT PRIMARY KEY,
    claim_id          TEXT,
    line_number       INTEGER,
    procedure_code    TEXT,
    modifier          TEXT,
    units             REAL DEFAULT 1.0,
    paid_amount       REAL DEFAULT 0.0,
    billed_amount     REAL DEFAULT 0.0,
    ndc_code          TEXT
);

CREATE TABLE IF NOT EXISTS referrals (
    referral_id           TEXT PRIMARY KEY,
    referring_provider_id TEXT,
    target_provider_id    TEXT,
    member_id             TEXT,
    referral_date         TEXT,
    claim_id              TEXT
);

-- ── Detection & Risk Tables ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    alert_id          TEXT PRIMARY KEY,
    rule_id           TEXT,
    rule_version      TEXT,
    entity_type       TEXT,
    entity_id         TEXT,
    claim_ids         TEXT,  -- JSON array
    severity          TEXT,
    est_dollars       REAL DEFAULT 0.0,
    fp_notes          TEXT,
    metadata          TEXT,  -- JSON object
    created_at        TEXT
);

CREATE TABLE IF NOT EXISTS networks (
    network_id              TEXT PRIMARY KEY,
    community_id            INTEGER,
    n_providers             INTEGER,
    hub_provider_id         TEXT,
    hard_link_score         REAL DEFAULT 0.0,
    referral_score          REAL DEFAULT 0.0,
    concentration_score     REAL DEFAULT 0.0,
    ownership_score         REAL DEFAULT 0.0,
    suspicious_claims       INTEGER DEFAULT 0,
    total_claims            INTEGER DEFAULT 0,
    total_exposure          REAL DEFAULT 0.0,
    triggered_rules         TEXT,  -- comma-separated
    hub_centrality          REAL DEFAULT 0.0,
    documented_group        INTEGER DEFAULT 0,
    network_feature_version TEXT
);

CREATE TABLE IF NOT EXISTS risk_scores (
    entity_type         TEXT,
    entity_id           TEXT,
    risk_score          REAL DEFAULT 0.0,
    anomaly_score       REAL DEFAULT 0.0,
    rule_score          REAL DEFAULT 0.0,
    network_score       REAL DEFAULT 0.0,
    future_risk_score   REAL DEFAULT 0.0,
    confidence          REAL DEFAULT 0.0,
    evidence_strength   REAL DEFAULT 0.0,
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS claim_ml (
    claim_id            TEXT PRIMARY KEY,
    anomaly_score       REAL DEFAULT 0.0,
    ml_prediction       TEXT,
    model_version       TEXT
);

-- ── Investigation & Case Management Tables ─────────────────────────
CREATE TABLE IF NOT EXISTS cases (
    case_id             TEXT PRIMARY KEY,
    entity_type         TEXT,
    entity_id           TEXT,
    entity_name         TEXT,
    status              TEXT DEFAULT 'NEW',
    priority            TEXT DEFAULT 'MEDIUM',
    risk_score          REAL DEFAULT 0.0,
    confidence          REAL DEFAULT 0.0,
    evidence_strength   REAL DEFAULT 0.0,
    exposure_low        REAL DEFAULT 0.0,
    exposure_high       REAL DEFAULT 0.0,
    members_affected    INTEGER DEFAULT 0,
    claims_count        INTEGER DEFAULT 0,
    why_flagged         TEXT,  -- JSON array
    top_reasons         TEXT,  -- JSON array
    benign_explanations TEXT,  -- JSON array
    risk_components     TEXT,  -- JSON object
    future_risk         TEXT,  -- JSON object
    network_id          TEXT,
    assigned_to         TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

CREATE TABLE IF NOT EXISTS case_evidence (
    evidence_id         TEXT PRIMARY KEY,
    case_id             TEXT,
    rule_id             TEXT,
    rule_name           TEXT,
    claim_id            TEXT,
    entity_id           TEXT,
    field_name          TEXT,
    field_value         TEXT,
    plain_text          TEXT,
    est_overpay         REAL DEFAULT 0.0,
    severity            TEXT DEFAULT 'MEDIUM',
    source_table        TEXT DEFAULT 'alerts',
    source_artifact     TEXT,
    timestamp           TEXT,
    fp_notes            TEXT
);

CREATE TABLE IF NOT EXISTS queue_items (
    case_id             TEXT PRIMARY KEY,
    rank                INTEGER,
    baseline_rank       INTEGER,
    entity_type         TEXT,
    entity_id           TEXT,
    entity_name         TEXT,
    risk                REAL,
    priority            TEXT,
    exposure_low        REAL,
    exposure_high       REAL,
    members_affected    INTEGER,
    severity            TEXT,
    evidence_strength   REAL,
    confidence          REAL,
    effort_hours        REAL,
    ev_per_hour         REAL,
    slot                INTEGER,
    top_reasons         TEXT  -- JSON array
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id              TEXT PRIMARY KEY,
    case_id             TEXT,
    action              TEXT,
    decision            TEXT,
    actor               TEXT DEFAULT 'system',
    notes               TEXT,
    payload             TEXT,  -- JSON object
    timestamp           TEXT
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    eval_id             TEXT PRIMARY KEY,
    eval_type           TEXT,  -- 'rules', 'rings', 'ablation'
    metrics             TEXT,  -- JSON object
    created_at          TEXT
);

-- ── Indexes for Investigation Queries ──────────────────────────────
CREATE INDEX IF NOT EXISTS idx_claims_provider ON claims(provider_id);
CREATE INDEX IF NOT EXISTS idx_claims_member ON claims(member_id);
CREATE INDEX IF NOT EXISTS idx_claims_service_date ON claims(service_date);
CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alerts(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_alerts_rule ON alerts(rule_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_case ON case_evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_claim ON case_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_cases_risk ON cases(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_cases_priority ON cases(priority);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_queue_rank ON queue_items(rank);
CREATE INDEX IF NOT EXISTS idx_queue_ev_hour ON queue_items(ev_per_hour DESC);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id);
CREATE INDEX IF NOT EXISTS idx_networks_hub ON networks(hub_provider_id);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Execute schema creation statements."""
    conn.executescript(SCHEMA_SQL)
