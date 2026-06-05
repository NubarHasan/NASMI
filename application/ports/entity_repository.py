from __future__ import annotations

from typing import Protocol

from core.types import EntityId
from knowledge.entity import Entity, EntityType


class EntityRepository(Protocol):

    def save(self, entity: Entity) -> None: ...

    def get(
        self,
        entity_id: EntityId,
    ) -> Entity | None: ...

    def exists(
        self,
        entity_id: EntityId,
    ) -> bool: ...

    def list_by_type(
        self,
        entity_type: EntityType,
    ) -> tuple[Entity, ...]: ...
