from __future__ import annotations

from typing import Protocol

from core.types import EntityId, FactId
from knowledge.fact import Fact, FactStatus


class FactRepository(Protocol):

    def save(self, fact: Fact) -> None: ...

    def get(self, fact_id: FactId) -> Fact | None: ...

    def exists(self, fact_id: FactId) -> bool: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[Fact, ...]: ...

    def list_by_entity_and_type(
        self,
        entity_id: EntityId,
        fact_type: str,
    ) -> tuple[Fact, ...]: ...

    def list_by_status(
        self,
        entity_id: EntityId,
        status: FactStatus,
    ) -> tuple[Fact, ...]: ...
