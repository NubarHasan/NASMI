from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.types import EntityId
from knowledge.conflict import Conflict, ConflictStatus


@runtime_checkable
class ConflictQueryService(Protocol):

    def list_conflicts(
        self,
        entity_id: EntityId,
    ) -> tuple[Conflict, ...]:
        """Return all conflicts linked to the given entity."""
        ...

    def list_conflicts_by_status(
        self,
        entity_id: EntityId,
        status: ConflictStatus,
    ) -> tuple[Conflict, ...]:
        """Return conflicts filtered by status for the given entity."""
        ...
