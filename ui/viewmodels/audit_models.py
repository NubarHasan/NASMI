from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from audit.audit_entry import AuditEventType
from core.types import AuditId, EntityId, JobId


@dataclass(frozen=True)
class AuditEntrySummary:
    audit_id: AuditId
    event_type: AuditEventType
    occurred_at: datetime
    message: str
    actor: str | None


@dataclass(frozen=True)
class AuditEntryDetail:
    audit_id: AuditId
    event_type: AuditEventType
    occurred_at: datetime
    message: str
    actor: str | None
    job_id: JobId | None
    subject_id: EntityId | None
    previous_hash: str | None
    entry_hash: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ViolationSummary:
    kind: str
    index: int | None
    detail: str


@dataclass(frozen=True)
class AuditVerificationSummary:
    is_valid: bool
    verified_at: datetime
    chain_length: int
    verified_entries: int
    violations: tuple[ViolationSummary, ...]
