from __future__ import annotations

from typing import Protocol

from knowledge.evidence_type import EvidenceType

from core.types import DocumentId, EntityId, EvidenceId
from knowledge.evidence import Evidence


class EvidenceRepository(Protocol):

    def save(self, evidence: Evidence) -> None: ...

    def get(self, evidence_id: EvidenceId) -> Evidence | None: ...

    def exists(self, evidence_id: EvidenceId) -> bool: ...

    def list_by_entity(self, entity_id: EntityId) -> tuple[Evidence, ...]: ...

    def list_by_document(self, document_id: DocumentId) -> tuple[Evidence, ...]: ...

    def list_by_type(
        self,
        entity_id: EntityId,
        evidence_type: EvidenceType,
    ) -> tuple[Evidence, ...]: ...
