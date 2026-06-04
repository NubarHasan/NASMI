from __future__ import annotations

from typing import Protocol

from output.application_package import ApplicationPackage
from output.package_status import PackageStatus

from core.types import ApplicationPackageId, EntityId, ProfileSnapshotId


class ApplicationPackageRepository(Protocol):

    def save(self, package: ApplicationPackage) -> None: ...

    def get(
        self,
        package_id: ApplicationPackageId,
    ) -> ApplicationPackage | None: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[ApplicationPackage, ...]: ...

    def list_by_snapshot(
        self,
        snapshot_id: ProfileSnapshotId,
    ) -> tuple[ApplicationPackage, ...]: ...

    def list_by_status(
        self,
        status: PackageStatus,
    ) -> tuple[ApplicationPackage, ...]: ...

    def mark_ready(
        self,
        package_id: ApplicationPackageId,
    ) -> None: ...

    def mark_delivered(
        self,
        package_id: ApplicationPackageId,
    ) -> None: ...
