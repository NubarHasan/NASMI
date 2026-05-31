from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.types import EntityId
from knowledge.profile import Profile


@runtime_checkable
class ProfileQueryService(Protocol):

    def get_profile(
        self,
        entity_id: EntityId,
    ) -> Profile | None: ...
