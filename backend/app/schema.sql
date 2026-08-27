-- Schema per design doc §12. Timestamps are ISO-8601 UTC strings set in
-- Python (not SQLite defaults) so the DDL stays portable to Postgres.

CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY,
    url          TEXT NOT NULL,
    domain       TEXT NOT NULL,
    name         TEXT,
    category     TEXT,
    profile_json TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    status      TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    cost_cents  INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER NOT NULL DEFAULT 0,
    tool_calls  INTEGER NOT NULL DEFAULT 0,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS competitors (
    id                     INTEGER PRIMARY KEY,
    run_id                 INTEGER NOT NULL REFERENCES runs(id),
    name                   TEXT NOT NULL,
    domain                 TEXT NOT NULL,
    relationship           TEXT,
    confidence             REAL,
    discovery_methods_json TEXT NOT NULL DEFAULT '[]',
    verified               INTEGER NOT NULL DEFAULT 0
);

-- competitor_id is NULL for sources about the original product itself.
CREATE TABLE IF NOT EXISTS sources (
    id            INTEGER PRIMARY KEY,
    run_id        INTEGER NOT NULL REFERENCES runs(id),
    competitor_id INTEGER REFERENCES competitors(id),
    url           TEXT NOT NULL,
    source_type   TEXT NOT NULL CHECK (source_type IN ('homepage', 'features', 'pricing', 'about', 'comparison', 'other')),
    fetched_at    TEXT NOT NULL,
    raw_text      TEXT,
    http_status   INTEGER,
    content_hash  TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES runs(id),
    competitor_id   INTEGER REFERENCES competitors(id),
    dimension       TEXT NOT NULL,
    value_json      TEXT NOT NULL,
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    extracted_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    id              INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES runs(id),
    section         TEXT NOT NULL CHECK (section IN ('executive_summary', 'competitive_landscape', 'feature_comparison', 'pricing_comparison')),
    text            TEXT NOT NULL,
    claim_type      TEXT NOT NULL CHECK (claim_type IN ('verified', 'reported', 'interpretation')),
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    confidence      REAL
);

CREATE TABLE IF NOT EXISTS eval_results (
    id           INTEGER PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES runs(id),
    metric       TEXT NOT NULL,
    score        REAL NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_product ON runs(product_id);
CREATE INDEX IF NOT EXISTS idx_competitors_run ON competitors(run_id);
CREATE INDEX IF NOT EXISTS idx_sources_run ON sources(run_id);
CREATE INDEX IF NOT EXISTS idx_findings_run ON findings(run_id);
CREATE INDEX IF NOT EXISTS idx_claims_run ON claims(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_results_run ON eval_results(run_id);
