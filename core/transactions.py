from __future__ import annotations

import contextlib
import shutil
import uuid
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Literal

from core.exceptions import FileSystemError, TransactionError
from core.filesystem import (
    copy_file,
    delete_file,
    ensure_directory,
    move_file,
    write_atomic,
)
from core.guards import require
from core.paths import TEMP_DIR


class TransactionState(StrEnum):
    OPEN = "open"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


class Transaction:
    def __init__(self) -> None:
        self._id: str = uuid.uuid4().hex
        self._ops: list[Callable[[], None]] = []
        self._state: TransactionState = TransactionState.OPEN
        self._backup_dir: Path = TEMP_DIR / f"tx_{self._id}"

    @property
    def state(self) -> TransactionState:
        return self._state

    def _require_open(self) -> None:
        require(
            self._state == TransactionState.OPEN,
            f"transaction is {self._state}, expected open",
        )

    def _backup_path(self, original: Path) -> Path:
        relative = original.as_posix().lstrip("/")
        return self._backup_dir / relative

    def write(self, path: Path, data: bytes) -> None:
        self._require_open()
        require(isinstance(path, Path), "path must be a Path")
        require(isinstance(data, bytes), "data must be bytes")
        existed = path.exists()
        backup: Path | None = None
        if existed:
            backup = self._backup_path(path)
            ensure_directory(backup.parent)
            copy_file(path, backup)
        write_atomic(path, data)

        def _rollback() -> None:
            if existed and backup and backup.is_file():
                write_atomic(path, backup.read_bytes())
            elif not existed and path.exists():
                delete_file(path)

        self._ops.append(_rollback)

    def copy(self, source: Path, destination: Path) -> None:
        self._require_open()
        require(isinstance(source, Path), "source must be a Path")
        require(isinstance(destination, Path), "destination must be a Path")
        existed = destination.exists()
        backup: Path | None = None
        if existed:
            backup = self._backup_path(destination)
            ensure_directory(backup.parent)
            copy_file(destination, backup)
        copy_file(source, destination)

        def _rollback() -> None:
            if existed and backup and backup.is_file():
                write_atomic(destination, backup.read_bytes())
            elif not existed and destination.exists():
                delete_file(destination)

        self._ops.append(_rollback)

    def move(self, source: Path, destination: Path) -> None:
        self._require_open()
        require(isinstance(source, Path), "source must be a Path")
        require(isinstance(destination, Path), "destination must be a Path")
        existed = destination.exists()
        backup: Path | None = None
        if existed:
            backup = self._backup_path(destination)
            ensure_directory(backup.parent)
            copy_file(destination, backup)
        move_file(source, destination)

        def _rollback() -> None:
            if destination.exists():
                move_file(destination, source)
            if existed and backup and backup.is_file():
                copy_file(backup, destination)

        self._ops.append(_rollback)

    def delete(self, path: Path) -> None:
        self._require_open()
        require(isinstance(path, Path), "path must be a Path")
        if not path.exists():
            return
        require(path.is_file(), f"delete() supports files only: {path}")
        backup = self._backup_path(path)
        ensure_directory(backup.parent)
        copy_file(path, backup)
        delete_file(path)

        def _rollback() -> None:
            if backup.is_file():
                write_atomic(path, backup.read_bytes())

        self._ops.append(_rollback)

    def commit(self) -> None:
        self._require_open()
        self._state = TransactionState.COMMITTED
        self._cleanup()

    def rollback(self) -> None:
        self._require_open()
        errors: list[str] = []
        for op in reversed(self._ops):
            try:
                op()
            except (FileSystemError, OSError) as exc:
                errors.append(str(exc))
        self._state = TransactionState.ROLLED_BACK
        self._cleanup()
        if errors:
            raise TransactionError(
                f"rollback completed with {len(errors)} error(s): {errors[0]}"
            )

    def _cleanup(self) -> None:
        if self._backup_dir.exists():
            with contextlib.suppress(OSError):
                shutil.rmtree(self._backup_dir)

    def __enter__(self) -> Transaction:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        if self._state != TransactionState.OPEN:
            return False
        if exc_type is None:
            self.commit()
        else:
            with contextlib.suppress(TransactionError):
                self.rollback()
        return False
