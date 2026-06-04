from __future__ import annotations

from typing import Protocol

from output.application_package_manifest import ApplicationPackageManifest

from core.types import EntityId, PackageId


class ApplicationPackageRepository(Protocol):

    def save(self, manifest: ApplicationPackageManifest) -> None: ...

    def get(
        self,
        package_id: PackageId,
    ) -> ApplicationPackageManifest | None: ...

    def exists(
        self,
        package_id: PackageId,
    ) -> bool: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[ApplicationPackageManifest, ...]: ...

    def get_latest_by_entity(
        self,
        entity_id: EntityId,
    ) -> ApplicationPackageManifest | None: ...
