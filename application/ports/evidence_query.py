from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.types import EntityId
from knowledge.evidence import Evidence


@runtime_checkable
class EvidenceQueryService(Protocol):

    def list_evidence(
        self,
        entity_id: EntityId,
    ) -> tuple[Evidence, ...]:
        """Return all evidence items linked to the given entity."""
        ...

    def list_evidence_for_field(
        self,
        entity_id: EntityId,
        field_name: str,
    ) -> tuple[Evidence, ...]:
        """Return evidence items linked to a specific field of the given entity."""
        ...
