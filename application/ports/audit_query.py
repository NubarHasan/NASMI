from __future__ import annotations

from typing import Protocol

from audit.audit_chain import AuditChain
from audit.audit_entry import AuditEntry, AuditEventType
from core.types import EntityId, JobId


class AuditQuery(Protocol):

    def get_chain(
        self,
        subject_id: EntityId,
    ) -> AuditChain: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[AuditEntry, ...]: ...

    def list_by_job(
        self,
        job_id: JobId,
    ) -> tuple[AuditEntry, ...]: ...

    def list_by_event_type(
        self,
        event_type: AuditEventType,
    ) -> tuple[AuditEntry, ...]: ...

    def get_latest_by_entity(
        self,
        entity_id: EntityId,
    ) -> AuditEntry | None: ...
