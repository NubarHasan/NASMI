from __future__ import annotations

from abc import ABC, abstractmethod

from audit.audit_chain import AuditChain
from audit.audit_entry import AuditEntry
from core.types import AuditId, EntityId, JobId


class AuditQueryService(ABC):

    @abstractmethod
    def get_by_id(
        self,
        audit_id: AuditId,
    ) -> AuditEntry | None: ...

    @abstractmethod
    def list_by_subject(
        self,
        subject_id: EntityId,
    ) -> tuple[AuditEntry, ...]: ...

    @abstractmethod
    def list_by_job(
        self,
        job_id: JobId,
    ) -> tuple[AuditEntry, ...]: ...

    @abstractmethod
    def get_chain(
        self,
        *,
        subject_id: EntityId | None = None,
        job_id: JobId | None = None,
    ) -> AuditChain: ...
