PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'merged', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    primary_language TEXT,
    merged_into TEXT REFERENCES entities(entity_id),
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    doc_type TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    language TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'processing', 'processed', 'failed')
    ),
    created_at TEXT NOT NULL,
    issued_at TEXT,
    expires_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    source_type TEXT NOT NULL CHECK (
        source_type IN ('document', 'user_input', 'import')
    ),
    created_at TEXT NOT NULL,
    document_id TEXT REFERENCES documents(document_id),
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    field_name TEXT NOT NULL,
    canonical_value TEXT,
    display_value TEXT NOT NULL,
    value_type TEXT NOT NULL CHECK (
        value_type IN (
            'string',
            'integer',
            'float',
            'boolean',
            'date',
            'datetime',
            'null'
        )
    ),
    confidence REAL NOT NULL CHECK (
        confidence >= 0.0
        AND confidence <= 1.0
    ),
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'accepted', 'rejected', 'superseded')
    ),
    source_stage TEXT NOT NULL,
    created_at TEXT NOT NULL,
    accepted_at TEXT,
    accepted_by TEXT,
    superseded_by TEXT REFERENCES facts(fact_id),
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    field_name TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (
        confidence >= 0.0
        AND confidence <= 1.0
    ),
    created_at TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '{}',
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS fact_evidence (
    fact_evidence_id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL REFERENCES facts(fact_id),
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
    role TEXT NOT NULL CHECK (
        role IN (
            'primary',
            'corroborating',
            'contradicting',
            'contextual'
        )
    ),
    created_at TEXT NOT NULL,
    UNIQUE (fact_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS provenance (
    provenance_id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL UNIQUE REFERENCES facts(fact_id),
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    decision_chain TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conflicts (
    conflict_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    field_name TEXT NOT NULL,
    fact_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('open', 'resolved', 'dismissed')),
    created_at TEXT NOT NULL,
    resolved_fact_id TEXT REFERENCES facts(fact_id),
    resolution_note TEXT NOT NULL DEFAULT '',
    resolved_by TEXT,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS review_cases (
    review_case_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    candidate_fact_id TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (
        confidence >= 0.0
        AND confidence <= 1.0
    ),
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (
        status IN (
            'PENDING',
            'ASSIGNED',
            'IN_REVIEW',
            'COMPLETED',
            'CANCELLED'
        )
    ),
    priority TEXT NOT NULL CHECK (
        priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')
    ),
    created_at TEXT NOT NULL,
    assigned_to TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES review_cases(review_case_id),
    decided_by TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (
        outcome IN ('APPROVED', 'REJECTED', 'EDITED', 'ESCALATED')
    ),
    rationale TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS audit_entries (
    audit_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'job_created',
            'job_started',
            'job_completed',
            'job_failed',
            'job_cancelled',
            'job_retrying',
            'document_imported',
            'ocr_completed',
            'entity_created',
            'entity_updated',
            'conflict_created',
            'conflict_resolved',
            'fact_accepted',
            'knowledge_updated',
            'validation_passed',
            'validation_failed',
            'package_generated',
            'package_assembled',
            'package_exported',
            'integrity_verified'
        )
    ),
    job_id TEXT,
    subject_id TEXT,
    occurred_at TEXT NOT NULL,
    actor TEXT,
    message TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    previous_hash TEXT,
    entry_hash TEXT NOT NULL,
    sequence_number INTEGER NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS output_documents (
    output_document_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES entities(entity_id),
    output_type TEXT NOT NULL CHECK (
        output_type IN (
            'profile_report',
            'knowledge_report',
            'fact_export',
            'evidence_report',
            'provenance_report',
            'conflict_report',
            'audit_report',
            'form_submission',
            'application_package'
        )
    ),
    output_format TEXT NOT NULL CHECK (
        output_format IN ('pdf', 'docx', 'json', 'xml', 'csv', 'zip')
    ),
    generated_at TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL CHECK (
        job_type IN (
            'document_import',
            'ocr',
            'extraction',
            'entity_resolution',
            'knowledge_build',
            'fact_acceptance',
            'profile_build',
            'form_fill',
            'export',
            'output_build'
        )
    ),
    priority TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'pending',
            'running',
            'completed',
            'failed',
            'cancelled',
            'retrying'
        )
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    context TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS form_templates (
    template_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS form_submissions (
    submission_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES form_templates(template_id),
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'submitted')),
    entries TEXT NOT NULL DEFAULT '[]',
    submitted_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_entity_id ON documents(entity_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_sources_entity_id ON sources(entity_id);
CREATE INDEX IF NOT EXISTS idx_sources_document_id ON sources(document_id);
CREATE INDEX IF NOT EXISTS idx_facts_entity_id ON facts(entity_id);
CREATE INDEX IF NOT EXISTS idx_facts_field_name ON facts(field_name);
CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status);
CREATE INDEX IF NOT EXISTS idx_facts_entity_field ON facts(entity_id, field_name);
CREATE INDEX IF NOT EXISTS idx_evidence_entity_id ON evidence(entity_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source_id ON evidence(source_id);
CREATE INDEX IF NOT EXISTS idx_evidence_field_name ON evidence(field_name);
CREATE INDEX IF NOT EXISTS idx_evidence_entity_field ON evidence(entity_id, field_name);
CREATE INDEX IF NOT EXISTS idx_fact_evidence_fact_id ON fact_evidence(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_evidence_evidence_id ON fact_evidence(evidence_id);
CREATE INDEX IF NOT EXISTS idx_provenance_fact_id ON provenance(fact_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entity_id ON provenance(entity_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_entity_id ON conflicts(entity_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);
CREATE INDEX IF NOT EXISTS idx_conflicts_field_name ON conflicts(field_name);
CREATE INDEX IF NOT EXISTS idx_review_cases_entity_id ON review_cases(entity_id);
CREATE INDEX IF NOT EXISTS idx_review_cases_status ON review_cases(status);
CREATE INDEX IF NOT EXISTS idx_review_cases_priority ON review_cases(priority);
CREATE INDEX IF NOT EXISTS idx_audit_entries_subject_id ON audit_entries(subject_id);
CREATE INDEX IF NOT EXISTS idx_audit_entries_job_id ON audit_entries(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_entries_event_type ON audit_entries(event_type);
CREATE INDEX IF NOT EXISTS idx_output_documents_subject ON output_documents(subject_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);
CREATE INDEX IF NOT EXISTS idx_form_submissions_template ON form_submissions(template_id);