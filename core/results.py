from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from core.exceptions import NasmiError

T = TypeVar("T")
U = TypeVar("U")


class Result(ABC, Generic[T]):

    @property
    @abstractmethod
    def ok(self) -> bool: ...

    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]: ...

    @property
    def failed(self) -> bool:
        return not self.ok

    @property
    def is_success(self) -> bool:
        return self.ok

    @property
    def is_failure(self) -> bool:
        return self.failed

    def __bool__(self) -> bool:
        return self.ok

    @abstractmethod
    def unwrap(self) -> T: ...

    @abstractmethod
    def unwrap_or(self, default: T) -> T: ...

    @abstractmethod
    def unwrap_error(self) -> NasmiError | None: ...

    @abstractmethod
    def map(self, fn: Callable[[T], U]) -> Result[U]: ...

    @abstractmethod
    def flat_map(self, fn: Callable[[T], Result[U]]) -> Result[U]: ...

    @abstractmethod
    def fold(
        self,
        on_success: Callable[[T], U],
        on_failure: Callable[[NasmiError], U],
    ) -> U: ...

    @abstractmethod
    def tap(self, fn: Callable[[T], None]) -> Result[T]: ...

    @abstractmethod
    def tap_error(self, fn: Callable[[NasmiError], None]) -> Result[T]: ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    @staticmethod
    def from_exception(
        exc: Exception,
        factory: Callable[[str], NasmiError],
        metadata: dict[str, Any] | None = None,
    ) -> Failure[Any]:
        error = factory(str(exc))
        merged_details = {**error.details, "original_exception": type(exc).__name__}
        error.details.clear()
        error.details.update(merged_details)
        return Failure(error=error, metadata=metadata or {})


@dataclass(frozen=True)
class Success(Result[T]):
    value: T
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def ok(self) -> bool:
        return True

    @property
    def error(self) -> NasmiError | None:
        return None

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def unwrap_error(self) -> NasmiError | None:
        return None

    def map(self, fn: Callable[[T], U]) -> Result[U]:
        return Success(
            value=fn(self.value),
            metadata=self.metadata.copy(),
        )

    def flat_map(self, fn: Callable[[T], Result[U]]) -> Result[U]:
        result = fn(self.value)
        merged = {**self.metadata, **result.metadata}
        if isinstance(result, Success):
            return Success(value=result.value, metadata=merged)
        if isinstance(result, Failure):
            return Failure(error=result.error, metadata=merged)
        return result

    def fold(
        self,
        on_success: Callable[[T], U],
        on_failure: Callable[[NasmiError], U],
    ) -> U:
        return on_success(self.value)

    def tap(self, fn: Callable[[T], None]) -> Result[T]:
        with suppress(Exception):
            fn(self.value)
        return self

    def tap_error(self, fn: Callable[[NasmiError], None]) -> Result[T]:
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class Failure(Result[T]):
    error: NasmiError
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def ok(self) -> bool:
        return False

    @property
    def value(self) -> T | None:
        return None

    def unwrap(self) -> T:
        raise self.error

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_error(self) -> NasmiError | None:
        return self.error

    def map(self, fn: Callable[[T], U]) -> Result[U]:
        return Failure(self.error, self.metadata.copy())

    def flat_map(self, fn: Callable[[T], Result[U]]) -> Result[U]:
        return Failure(self.error, self.metadata.copy())

    def fold(
        self,
        on_success: Callable[[T], U],
        on_failure: Callable[[NasmiError], U],
    ) -> U:
        return on_failure(self.error)

    def tap(self, fn: Callable[[T], None]) -> Result[T]:
        return self

    def tap_error(self, fn: Callable[[NasmiError], None]) -> Result[T]:
        with suppress(Exception):
            fn(self.error)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": self.error.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


def success(value: T, metadata: dict[str, Any] | None = None) -> Success[T]:
    return Success(value=value, metadata=metadata or {})


def failure(error: NasmiError, metadata: dict[str, Any] | None = None) -> Failure[Any]:
    return Failure(error=error, metadata=metadata or {})
