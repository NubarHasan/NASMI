from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from audit.integrity_result import IntegrityResult, IntegrityViolation
from core.guards import require
from core.time import format_timestamp, parse_timestamp


@dataclass(frozen=True)
class VerificationResult:
    integrity_result: IntegrityResult
    verified_at: datetime
    chain_length: int
    verified_entries: int

    def __post_init__(self) -> None:
        require(
            isinstance(self.integrity_result, IntegrityResult),
            "integrity_result must be an IntegrityResult",
        )
        require(
            isinstance(self.verified_at, datetime),
            "verified_at must be a datetime",
        )
        require(
            self.chain_length >= 0,
            "chain_length must be non-negative",
        )
        require(
            self.verified_entries >= 0,
            "verified_entries must be non-negative",
        )
        require(
            self.verified_entries <= self.chain_length,
            "verified_entries must not exceed chain_length",
        )

    @property
    def is_valid(self) -> bool:
        return self.integrity_result.is_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "verified_at": format_timestamp(self.verified_at),
            "chain_length": self.chain_length,
            "verified_entries": self.verified_entries,
            "integrity_result": self.integrity_result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
        require(isinstance(data, dict), "data must be a dictionary")
        integrity_data = data["integrity_result"]
        violations = tuple(
            IntegrityViolation.from_dict(v) for v in integrity_data["violations"]
        )
        integrity_result = IntegrityResult(
            is_valid=integrity_data["is_valid"],
            violations=violations,
        )
        return cls(
            integrity_result=integrity_result,
            verified_at=parse_timestamp(data["verified_at"]),
            chain_length=data["chain_length"],
            verified_entries=data["verified_entries"],
        )
