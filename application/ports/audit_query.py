from __future__ import annotations

from datetime import datetime
from typing import Protocol

from audit.audit_event import AuditEvent
from knowledge.provenance_step import ProvenanceStep

from core.types import DocumentId, EntityId, FactId, ReviewerId


class AuditQuery(Protocol):

    def list_events_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[AuditEvent, ...]: ...

    def list_events_by_fact(
        self,
        fact_id: FactId,
    ) -> tuple[AuditEvent, ...]: ...

    def list_events_by_reviewer(
        self,
        reviewer_id: ReviewerId,
    ) -> tuple[AuditEvent, ...]: ...

    def list_events_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> tuple[AuditEvent, ...]: ...

    def list_steps_by_fact(
        self,
        fact_id: FactId,
    ) -> tuple[ProvenanceStep, ...]: ...

    def list_steps_by_document(
        self,
        document_id: DocumentId,
    ) -> tuple[ProvenanceStep, ...]: ...

    def verify_fact_integrity(
        self,
        fact_id: FactId,
    ) -> bool: ...
