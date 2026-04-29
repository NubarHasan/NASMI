-- ============================================================
-- NASMI Database Schema
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ------------------------------------------------------------
-- 1. documents
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT NOT NULL,
    file_type     TEXT NOT NULL,
    file_size     REAL,
    file_hash     TEXT UNIQUE,
    uploaded_at   TEXT DEFAULT (datetime('now')),
    status        TEXT DEFAULT 'pending',
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_documents_status   ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_filehash ON documents(file_hash);

-- ------------------------------------------------------------
-- 2. document_versions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_versions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    changed_by    TEXT,
    changed_at    TEXT DEFAULT (datetime('now')),
    note          TEXT,
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_docver_document_id ON document_versions(document_id);

-- ------------------------------------------------------------
-- 3. entities
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER NOT NULL,
    entity_type   TEXT NOT NULL,
    entity_value  TEXT NOT NULL,
    confidence    REAL DEFAULT 0.0,
    source        TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_entities_document_id  ON entities(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_entity_type  ON entities(entity_type);

-- ------------------------------------------------------------
-- 4. knowledge
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    field         TEXT NOT NULL UNIQUE,
    value         TEXT,
    confidence    REAL DEFAULT 0.0,
    source        TEXT,
    verified      INTEGER DEFAULT 0,
    updated_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_knowledge_field ON knowledge(field);

-- ------------------------------------------------------------
-- 5. knowledge_history
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id  INTEGER NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    changed_by    TEXT,
    changed_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id)
);

CREATE INDEX IF NOT EXISTS idx_knowledgehist_knowledge_id ON knowledge_history(knowledge_id);

-- ------------------------------------------------------------
-- 6. review_queue
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id     INTEGER,
    field         TEXT,
    value         TEXT,
    priority      INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'pending',
    assigned_to   TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    resolved_at   TEXT,
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_reviewqueue_status   ON review_queue(status);
CREATE INDEX IF NOT EXISTS idx_reviewqueue_priority ON review_queue(priority);

-- ------------------------------------------------------------
-- 7. contradictions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contradictions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    field         TEXT NOT NULL,
    value_a       TEXT,
    value_b       TEXT,
    source_a      TEXT,
    source_b      TEXT,
    status        TEXT DEFAULT 'open',
    resolved_at   TEXT,
    resolution    TEXT,
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_contradictions_status ON contradictions(status);
CREATE INDEX IF NOT EXISTS idx_contradictions_field  ON contradictions(field);

-- ------------------------------------------------------------
-- 8. address_fields
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS address_fields (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    label         TEXT NOT NULL,
    value         TEXT,
    field_type    TEXT,
    document_id   INTEGER,
    created_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_addressfields_document_id ON address_fields(document_id);

-- ------------------------------------------------------------
-- 9. identity_core
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_core (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT,
    birth_date    TEXT,
    nationality   TEXT,
    id_number     TEXT UNIQUE,
    status        TEXT DEFAULT 'active',
    created_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_identitycore_id_number ON identity_core(id_number);

-- ------------------------------------------------------------
-- 10. signed_claims
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS signed_claims (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_id   INTEGER NOT NULL,
    claim_type    TEXT NOT NULL,
    claim_value   TEXT,
    signed_by     TEXT,
    signed_at     TEXT DEFAULT (datetime('now')),
    valid_until   TEXT,
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (identity_id) REFERENCES identity_core(id)
);

CREATE INDEX IF NOT EXISTS idx_signedclaims_identity_id ON signed_claims(identity_id);

-- ------------------------------------------------------------
-- 11. audit_log
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    action        TEXT NOT NULL,
    table_name    TEXT,
    record_id     INTEGER,
    performed_by  TEXT,
    performed_at  TEXT DEFAULT (datetime('now')),
    details       TEXT,
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_auditlog_table_name  ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_auditlog_performed_at ON audit_log(performed_at);

-- ------------------------------------------------------------
-- 12. system_logs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    level         TEXT NOT NULL,
    module        TEXT,
    message       TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_systemlogs_level  ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_systemlogs_module ON system_logs(module);

-- ------------------------------------------------------------
-- 13. exports
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type   TEXT NOT NULL,
    file_path     TEXT,
    created_by    TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    status        TEXT DEFAULT 'pending',
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_exports_status ON exports(status);

-- ------------------------------------------------------------
-- 14. timeline_events
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS timeline_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_id   INTEGER,
    event_type    TEXT NOT NULL,
    event_date    TEXT,
    description   TEXT,
    source        TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (identity_id) REFERENCES identity_core(id)
);

CREATE INDEX IF NOT EXISTS idx_timelineevents_identity_id ON timeline_events(identity_id);
CREATE INDEX IF NOT EXISTS idx_timelineevents_event_date  ON timeline_events(event_date);

-- ------------------------------------------------------------
-- 15. processing_jobs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processing_jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER,
    job_type      TEXT NOT NULL,
    status        TEXT DEFAULT 'queued',
    started_at    TEXT,
    finished_at   TEXT,
    error         TEXT,
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_processingjobs_status      ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processingjobs_document_id ON processing_jobs(document_id);

-- ------------------------------------------------------------
-- 16. settings
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key           TEXT NOT NULL UNIQUE,
    value         TEXT,
    updated_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

-- ------------------------------------------------------------
-- 17. expiry_alerts
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expiry_alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER,
    field         TEXT NOT NULL,
    value         TEXT,
    expiry_date   TEXT NOT NULL,
    days_remaining INTEGER,
    severity      TEXT DEFAULT 'info',
    status        TEXT DEFAULT 'active',
    notified_at   TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    metadata      TEXT DEFAULT '{}',
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_expiryalerts_status      ON expiry_alerts(status);
CREATE INDEX IF NOT EXISTS idx_expiryalerts_expiry_date ON expiry_alerts(expiry_date);
CREATE INDEX IF NOT EXISTS idx_expiryalerts_severity    ON expiry_alerts(severity);