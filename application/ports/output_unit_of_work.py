from __future__ import annotations

from typing import Protocol

from application.ports.application_package_repository import (
    ApplicationPackageRepository,
)
from application.ports.profile_snapshot_repository import OutputDocumentRepository


class OutputUnitOfWork(Protocol):

    snapshots: OutputDocumentRepository
    packages: ApplicationPackageRepository

    def __enter__(self) -> OutputUnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
