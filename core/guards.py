from __future__ import annotations

from pathlib import Path
from typing import Any

from core.exceptions import StateError, ValidationError


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def invariant(condition: bool, message: str) -> None:
    if not condition:
        raise StateError(message)


def assert_true(condition: bool, message: str) -> None:
    require(condition, message)


def assert_false(condition: bool, message: str) -> None:
    require(not condition, message)


def assert_state(condition: bool, message: str) -> None:
    invariant(condition, message)


def assert_not_none(value: Any, message: str) -> None:
    require(value is not None, message)


def assert_instance(
    value: Any,
    expected_type: type | tuple[type, ...],
    message: str,
) -> None:
    require(isinstance(value, expected_type), message)


def assert_non_empty(value: Any, message: str) -> None:
    require(bool(value), message)


def assert_not_empty_string(value: str, message: str) -> None:
    require(isinstance(value, str), message)
    require(bool(value.strip()), message)


def assert_equal(actual: Any, expected: Any, message: str) -> None:
    require(actual == expected, message)


def assert_positive(value: int | float, message: str) -> None:
    require(isinstance(value, (int, float)), message)
    require(value > 0, message)


def assert_non_negative(value: int | float, message: str) -> None:
    require(isinstance(value, (int, float)), message)
    require(value >= 0, message)


def assert_file_exists(path: Path, message: str) -> None:
    require(isinstance(path, Path), message)
    require(path.exists(), message)
    require(path.is_file(), message)


def assert_directory_exists(path: Path, message: str) -> None:
    require(isinstance(path, Path), message)
    require(path.exists(), message)
    require(path.is_dir(), message)
