from __future__ import annotations

from typing import Protocol

from output.profile_snapshot import ProfileSnapshot

from core.types import EntityId, ProfileSnapshotId


class ProfileSnapshotRepository(Protocol):

    def save(self, snapshot: ProfileSnapshot) -> None: ...

    def get(
        self,
        snapshot_id: ProfileSnapshotId,
    ) -> ProfileSnapshot | None: ...

    def get_latest_by_entity(
        self,
        entity_id: EntityId,
    ) -> ProfileSnapshot | None: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[ProfileSnapshot, ...]: ...
