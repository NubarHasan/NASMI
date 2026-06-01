from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.types import EntityId, FactId
from knowledge.provenance import Provenance


@runtime_checkable
class ProvenanceQueryService(Protocol):

    def list_provenance(
        self,
        entity_id: EntityId,
    ) -> tuple[Provenance, ...]:
        """Return all Provenance records for the given entity."""
        ...

    def get_provenance_by_fact(
        self,
        fact_id: FactId,
    ) -> Provenance | None:
        """Return the Provenance record for a specific fact, or None."""
        ...
