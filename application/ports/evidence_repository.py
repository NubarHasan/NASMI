from __future__ import annotations

from typing import Protocol

from core.types import DocumentId, EntityId, EvidenceId, SourceId
from knowledge.evidence import Evidence


class EvidenceRepository(Protocol):

    def save(self, evidence: Evidence) -> None: ...

    def get(
        self,
        evidence_id: EvidenceId,
    ) -> Evidence | None: ...

    def exists(
        self,
        evidence_id: EvidenceId,
    ) -> bool: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[Evidence, ...]: ...

    def list_by_source(
        self,
        source_id: SourceId,
    ) -> tuple[Evidence, ...]: ...

    def list_by_document(
        self,
        document_id: DocumentId,
    ) -> tuple[Evidence, ...]: ...

    def list_by_field(
        self,
        entity_id: EntityId,
        field_name: str,
    ) -> tuple[Evidence, ...]: ...
