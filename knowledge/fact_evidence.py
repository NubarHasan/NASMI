from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_fact_evidence_id,
    is_valid_evidence_id,
    is_valid_fact_evidence_id,
    is_valid_fact_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import EvidenceId, FactEvidenceId, FactId


class FactEvidenceRole:
    PRIMARY = "primary"
    CORROBORATING = "corroborating"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"


@dataclass(frozen=True)
class FactEvidence:
    fact_evidence_id: FactEvidenceId
    fact_id: FactId
    evidence_id: EvidenceId
    role: str
    created_at: str

    def __post_init__(self) -> None:
        require(
            is_valid_fact_evidence_id(self.fact_evidence_id),
            f"invalid fact_evidence_id: {self.fact_evidence_id!r}",
        )
        require(
            is_valid_fact_id(self.fact_id),
            f"invalid fact_id: {self.fact_id!r}",
        )
        require(
            is_valid_evidence_id(self.evidence_id),
            f"invalid evidence_id: {self.evidence_id!r}",
        )
        require(
            isinstance(self.role, str) and bool(self.role.strip()),
            "role must be a non-empty string",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_evidence_id": self.fact_evidence_id,
            "fact_id": self.fact_id,
            "evidence_id": self.evidence_id,
            "role": self.role,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactEvidence:
        return cls(
            fact_evidence_id=FactEvidenceId(data["fact_evidence_id"]),
            fact_id=FactId(data["fact_id"]),
            evidence_id=EvidenceId(data["evidence_id"]),
            role=data["role"],
            created_at=data["created_at"],
        )

    @classmethod
    def create(
        cls,
        fact_id: str,
        evidence_id: str,
        role: str,
    ) -> FactEvidence:
        require(is_valid_fact_id(fact_id), f"invalid fact_id: {fact_id!r}")
        require(
            is_valid_evidence_id(evidence_id), f"invalid evidence_id: {evidence_id!r}"
        )
        require(
            isinstance(role, str) and bool(role.strip()),
            "role must be a non-empty string",
        )
        return cls(
            fact_evidence_id=generate_fact_evidence_id(),
            fact_id=FactId(fact_id),
            evidence_id=EvidenceId(evidence_id),
            role=role,
            created_at=utcnow_iso(),
        )
