from __future__ import annotations

from typing import Protocol

from knowledge.conflict_status import ConflictStatus

from core.types import ConflictId, EntityId, FactId
from knowledge.conflict import Conflict


class ConflictRepository(Protocol):

    def save(self, conflict: Conflict) -> None: ...

    def get(self, conflict_id: ConflictId) -> Conflict | None: ...

    def exists_between(
        self,
        fact_id_a: FactId,
        fact_id_b: FactId,
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

    def resolve(self, conflict_id: ConflictId) -> None: ...

    def dismiss(self, conflict_id: ConflictId) -> None: ...

    def supersede(self, conflict_id: ConflictId) -> None: ...
