from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, TypeVar

from core.guards import require

T = TypeVar("T")

_DEFAULT_MAX_SIZE: int = 256
_DEFAULT_TTL: float | None = None


@dataclass(frozen=True)
class CacheConfig:
    max_size: int = _DEFAULT_MAX_SIZE
    ttl: float | None = _DEFAULT_TTL

    def __post_init__(self) -> None:
        require(self.max_size >= 1, "max_size must be >= 1")
        require(
            self.ttl is None or self.ttl > 0.0,
            "ttl must be > 0 or None",
        )


@dataclass
class _Entry(Generic[T]):
    value: T
    expire_at: float | None


class Cache(Generic[T]):
    def __init__(self, config: CacheConfig | None = None) -> None:
        self._config: CacheConfig = config or CacheConfig()
        self._store: OrderedDict[str, _Entry[T]] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: str) -> T | None:
        require(isinstance(key, str) and bool(key), "key must be a non-empty string")
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if self._is_expired(entry):
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: str, value: T, ttl: float | None = _DEFAULT_TTL) -> None:
        require(isinstance(key, str) and bool(key), "key must be a non-empty string")
        if ttl is not None:
            require(ttl > 0.0, "ttl must be > 0")
        effective_ttl = ttl if ttl is not None else self._config.ttl
        expire_at = (
            time.monotonic() + effective_ttl if effective_ttl is not None else None
        )
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = _Entry(value=value, expire_at=expire_at)
            self._prune_expired()
            self._evict_if_needed()

    def delete(self, key: str) -> None:
        require(isinstance(key, str) and bool(key), "key must be a non-empty string")
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def keys(self) -> list[str]:
        with self._lock:
            self._prune_expired()
            return list(self._store.keys())

    def items(self) -> list[tuple[str, T]]:
        with self._lock:
            self._prune_expired()
            return [(k, e.value) for k, e in self._store.items()]

    def __len__(self) -> int:
        with self._lock:
            self._prune_expired()
            return len(self._store)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if self._is_expired(entry):
                del self._store[key]
                return False
            return True

    def _prune_expired(self) -> None:
        expired = [k for k, e in self._store.items() if self._is_expired(e)]
        for k in expired:
            del self._store[k]

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._config.max_size:
            self._store.popitem(last=False)

    @staticmethod
    def _is_expired(entry: _Entry[T]) -> bool:
        return entry.expire_at is not None and time.monotonic() > entry.expire_at
