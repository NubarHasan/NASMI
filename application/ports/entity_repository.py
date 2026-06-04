from __future__ import annotations

from typing import Protocol

from knowledge.entity_type import EntityType

from core.types import EntityId, ExternalRef
from knowledge.entity import Entity


class EntityRepository(Protocol):

    def save(self, entity: Entity) -> None: ...

    def get(self, entity_id: EntityId) -> Entity | None: ...

    def get_by_external_ref(
        self,
        entity_type: EntityType,
        external_ref: ExternalRef,
    ) -> Entity | None: ...

    def exists(self, entity_id: EntityId) -> bool: ...

    def exists_by_external_ref(
        self,
        entity_type: EntityType,
        external_ref: ExternalRef,
    ) -> bool: ...

    def list_by_type(
        self,
        entity_type: EntityType,
    ) -> tuple[Entity, ...]: ...
