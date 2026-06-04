from __future__ import annotations

from typing import Protocol

from core.types import EntityId, FactId
from knowledge.fact import Fact
from knowledge.knowledge_fact_type import KnowledgeFactType


class FactRepository(Protocol):

    def save(self, fact: Fact) -> None: ...

    def get(self, fact_id: FactId) -> Fact | None: ...

    def exists(self, fact_id: FactId) -> bool: ...

    def list_by_entity(self, entity_id: EntityId) -> tuple[Fact, ...]: ...

    def list_by_entity_and_type(
        self,
        entity_id: EntityId,
        fact_type: KnowledgeFactType,
    ) -> tuple[Fact, ...]: ...

    def list_pending(self, entity_id: EntityId) -> tuple[Fact, ...]: ...

    def list_accepted(self, entity_id: EntityId) -> tuple[Fact, ...]: ...

    def list_rejected(self, entity_id: EntityId) -> tuple[Fact, ...]: ...

    def list_archived(self, entity_id: EntityId) -> tuple[Fact, ...]: ...

    def accept(self, fact_id: FactId) -> None: ...

    def reject(self, fact_id: FactId) -> None: ...

    def archive(
        self,
        fact_id: FactId,
        reason: str,
        archived_by: str,
    ) -> None: ...

    def restore(self, fact_id: FactId) -> None: ...
