from __future__ import annotations

from typing import Protocol

from core.types import EntityId, FactId, ProvenanceId
from knowledge.provenance import Provenance


class ProvenanceRepository(Protocol):

    def save(self, provenance: Provenance) -> None: ...

    def get(
        self,
        provenance_id: ProvenanceId,
    ) -> Provenance | None: ...

    def exists(
        self,
        provenance_id: ProvenanceId,
    ) -> bool: ...

    def get_by_fact(
        self,
        fact_id: FactId,
    ) -> Provenance | None: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[Provenance, ...]: ...
