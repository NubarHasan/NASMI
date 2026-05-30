from __future__ import annotations

import contextlib
import sys
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import IO, ClassVar

from core.exceptions import LockError
from core.filesystem import ensure_directory
from core.guards import require

_DEFAULT_TIMEOUT: float = 10.0
_POLL_INTERVAL: float = 0.05


class FileLock:
    def __init__(self, path: Path, timeout: float = _DEFAULT_TIMEOUT) -> None:
        require(isinstance(path, Path), "path must be a Path")
        require(timeout >= 0.0, "timeout must be >= 0")
        self._lock_path: Path = path.with_suffix(path.suffix + ".lock")
        self._timeout: float = timeout
        self._file: IO[bytes] | None = None
        self._fd: int | None = None

    @property
    def lock_path(self) -> Path:
        return self._lock_path

    def acquire(self) -> None:
        ensure_directory(self._lock_path.parent)
        deadline = time.monotonic() + self._timeout
        file = open(self._lock_path, "a+b")  # noqa: SIM115
        self._file = file
        self._fd = file.fileno()
        while True:
            try:
                _platform_lock(self._fd)
                return
            except OSError as exc:
                if time.monotonic() >= deadline:
                    self._close()
                    raise LockError(
                        f"could not acquire lock within {self._timeout}s: "
                        f"{self._lock_path}"
                    ) from exc
                time.sleep(_POLL_INTERVAL)

    def release(self) -> None:
        if self._file is None:
            return
        fd = self._fd
        assert fd is not None
        try:
            _platform_unlock(fd)
        finally:
            self._close()
            with contextlib.suppress(OSError):
                self._lock_path.unlink(missing_ok=True)

    def _close(self) -> None:
        if self._file is not None:
            with contextlib.suppress(OSError):
                self._file.close()
            self._file = None
            self._fd = None

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()


class MemoryLock:
    _registry: ClassVar[dict[str, threading.Lock]] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, key: str, timeout: float = _DEFAULT_TIMEOUT) -> None:
        require(bool(key), "key must be a non-empty string")
        require(timeout >= 0.0, "timeout must be >= 0")
        self._key: str = key
        self._timeout: float = timeout
        self._lock: threading.Lock = self._get_or_create(key)

    @classmethod
    def _get_or_create(cls, key: str) -> threading.Lock:
        with cls._registry_lock:
            if key not in cls._registry:
                cls._registry[key] = threading.Lock()
            return cls._registry[key]

    def acquire(self) -> None:
        acquired = self._lock.acquire(timeout=self._timeout)
        if not acquired:
            raise LockError(
                f"could not acquire memory lock within {self._timeout}s: "
                f"key={self._key!r}"
            )

    def release(self) -> None:
        try:
            self._lock.release()
        except RuntimeError as exc:
            raise LockError(f"lock release failed: key={self._key!r}") from exc

    def __enter__(self) -> MemoryLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()


def _platform_lock(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _platform_unlock(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
