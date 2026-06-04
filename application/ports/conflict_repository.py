from __future__ import annotations

from typing import Protocol

from core.types import ConflictId, EntityId, FactId
from knowledge.conflict import Conflict, ConflictStatus


class ConflictRepository(Protocol):

    def save(self, conflict: Conflict) -> None: ...

    def get(
        self,
        conflict_id: ConflictId,
    ) -> Conflict | None: ...

    def exists(
        self,
        conflict_id: ConflictId,
    ) -> bool: ...

    def exists_for_facts(
        self,
        fact_ids: tuple[FactId, ...],
    ) -> bool: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[Conflict, ...]: ...

    def list_by_fact(
        self,
        fact_id: FactId,
    ) -> tuple[Conflict, ...]: ...

    def list_by_status(
        self,
        entity_id: EntityId,
        status: ConflictStatus,
    ) -> tuple[Conflict, ...]: ...
