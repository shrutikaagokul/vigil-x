-- ============================================================
-- Vigil-X — Core Schema
-- Represents the minimum tables needed for FWA detection.
-- This is the conceptual schema; actual data lives in pandas DataFrames
-- loaded from parquet/CSV files for hackathon speed.
-- ============================================================

CREATE TABLE IF NOT EXISTS providers (
    provider_id     TEXT PRIMARY KEY,
    npi             TEXT,
    name            TEXT,
    specialty       TEXT,
    latitude        REAL,
    longitude       REAL,
    address         TEXT,
    suite           TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    county          TEXT,
    facility_type   TEXT,       -- 'clinic', 'hospital', 'residential', 'virtual_office'
    owner_name      TEXT,
    owner_entity    TEXT,
    registered_agent TEXT,
    bank_hash       TEXT,       -- hashed bank routing/account
    tin_hash        TEXT,       -- hashed TIN
    group_id        TEXT,       -- documented medical group
    enrolled_date   TEXT
);

CREATE TABLE IF NOT EXISTS members (
    member_id       TEXT PRIMARY KEY,
    name            TEXT,
    dob             TEXT,
    gender          TEXT,
    latitude        REAL,
    longitude       REAL,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    county          TEXT,
    plan_type       TEXT,
    enrolled_date   TEXT
);

CREATE TABLE IF NOT EXISTS facilities (
    facility_id     TEXT PRIMARY KEY,
    name            TEXT,
    facility_type   TEXT,       -- 'hospital', 'clinic', 'lab', 'nursing', 'residential', 'virtual_office'
    latitude        REAL,
    longitude       REAL,
    address         TEXT,
    suite           TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    county          TEXT,
    owner_name      TEXT,
    owner_entity    TEXT,
    capacity        INTEGER
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id        TEXT PRIMARY KEY,
    member_id       TEXT REFERENCES members(member_id),
    provider_id     TEXT REFERENCES providers(provider_id),
    facility_id     TEXT,
    referring_provider_id TEXT,
    service_date    TEXT,       -- YYYY-MM-DD
    service_start_ts TEXT,      -- YYYY-MM-DD HH:MM:SS
    service_end_ts  TEXT,
    service_minutes REAL,
    pos_code        TEXT,       -- place of service
    procedure_code  TEXT,
    diagnosis_code  TEXT,
    paid_amount     REAL,
    billed_amount   REAL,
    allowed_amount  REAL,
    status          TEXT,       -- 'paid', 'denied', 'pending'
    claim_type      TEXT        -- 'professional', 'institutional', 'pharmacy'
);

CREATE TABLE IF NOT EXISTS claim_lines (
    line_id         TEXT PRIMARY KEY,
    claim_id        TEXT REFERENCES claims(claim_id),
    line_number     INTEGER,
    procedure_code  TEXT,
    modifier        TEXT,
    units           REAL,
    paid_amount     REAL,
    billed_amount   REAL,
    ndc_code        TEXT
);

CREATE TABLE IF NOT EXISTS referrals (
    referral_id     TEXT PRIMARY KEY,
    referring_provider_id TEXT REFERENCES providers(provider_id),
    target_provider_id TEXT REFERENCES providers(provider_id),
    member_id       TEXT REFERENCES members(member_id),
    referral_date   TEXT,
    claim_id        TEXT
);

-- Ground truth tables (ONLY for evaluation, NEVER for detection)
CREATE TABLE IF NOT EXISTS gt_scenarios (
    scenario_id     TEXT PRIMARY KEY,
    scenario_type   TEXT,
    description     TEXT,
    ring_id         TEXT,
    provider_ids    TEXT,       -- comma-separated
    expected_rules  TEXT        -- comma-separated
);

CREATE TABLE IF NOT EXISTS gt_claim_labels (
    claim_id        TEXT PRIMARY KEY,
    scenario_id     TEXT,
    is_suspicious   INTEGER,
    label_reason    TEXT
);

CREATE TABLE IF NOT EXISTS gt_entity_labels (
    entity_type     TEXT,
    entity_id       TEXT,
    scenario_id     TEXT,
    is_suspicious   INTEGER,
    label_reason    TEXT,
    PRIMARY KEY (entity_type, entity_id)
);
