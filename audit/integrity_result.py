from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from core.guards import require


class ViolationKind(StrEnum):
    # Structural
    INVALID_ENTRY_TYPE = "invalid_entry_type"
    DUPLICATE_AUDIT_ID = "duplicate_audit_id"
    GENESIS_HASH_NOT_NONE = "genesis_hash_not_none"
    BROKEN_HASH_LINK = "broken_hash_link"
    ORDERING_VIOLATION = "ordering_violation"

    # Cryptographic
    INVALID_HMAC = "invalid_hmac"


@dataclass(frozen=True)
class IntegrityViolation:
    kind: ViolationKind
    index: int | None
    detail: str

    def __post_init__(self) -> None:
        require(isinstance(self.kind, ViolationKind), "kind must be a ViolationKind")
        require(self.index is None or self.index >= 0, "index must be non-negative")
        require(bool(self.detail), "detail must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "index": self.index,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrityViolation:
        require(isinstance(data, dict), "data must be a dictionary")
        return cls(
            kind=ViolationKind(data["kind"]),
            index=data.get("index"),
            detail=data["detail"],
        )


@dataclass(frozen=True)
class IntegrityResult:
    is_valid: bool
    violations: tuple[IntegrityViolation, ...]

    def __post_init__(self) -> None:
        require(
            isinstance(self.violations, tuple),
            "violations must be a tuple",
        )
        require(
            all(isinstance(v, IntegrityViolation) for v in self.violations),
            "all violations must be IntegrityViolation instances",
        )
        require(
            not self.is_valid or len(self.violations) == 0,
            "is_valid=True must have no violations",
        )
        require(
            self.is_valid or len(self.violations) > 0,
            "is_valid=False must have at least one violation",
        )

    def first_violation(self) -> IntegrityViolation | None:
        return self.violations[0] if self.violations else None

    def by_kind(self, kind: ViolationKind) -> tuple[IntegrityViolation, ...]:
        return tuple(v for v in self.violations if v.kind == kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "violations": [v.to_dict() for v in self.violations],
        }

    @classmethod
    def passed(cls) -> IntegrityResult:
        return cls(is_valid=True, violations=())

    @classmethod
    def failed(cls, violations: Iterable[IntegrityViolation]) -> IntegrityResult:
        violations_tuple = tuple(violations)
        require(
            len(violations_tuple) > 0,
            "failed() requires at least one violation",
        )
        require(
            all(isinstance(v, IntegrityViolation) for v in violations_tuple),
            "all violations must be IntegrityViolation instances",
        )
        return cls(is_valid=False, violations=violations_tuple)
