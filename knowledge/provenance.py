from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_provenance_id,
    is_valid_entity_id,
    is_valid_evidence_id,
    is_valid_fact_id,
    is_valid_provenance_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import EntityId, EvidenceId, FactId, ProvenanceId


class ProvenanceActor:
    OCR = "ocr"
    VALIDATOR = "validator"
    REVIEWER = "reviewer"
    USER = "user"
    SYSTEM = "system"


@dataclass(frozen=True)
class ProvenanceStep:
    step_order: int
    action: str
    actor: str
    occurred_at: str
    evidence_id: EvidenceId | None = field(default=None)
    note: str = field(default="")

    def __post_init__(self) -> None:
        require(
            self.step_order >= 0,
            f"step_order must be >= 0, got {self.step_order}",
        )
        require(
            isinstance(self.action, str) and bool(self.action.strip()),
            "action must be a non-empty string",
        )
        require(
            isinstance(self.actor, str) and bool(self.actor.strip()),
            "actor must be a non-empty string",
        )
        require(
            is_valid_timestamp(self.occurred_at),
            f"invalid occurred_at: {self.occurred_at!r}",
        )
        if self.evidence_id is not None:
            require(
                is_valid_evidence_id(self.evidence_id),
                f"invalid evidence_id: {self.evidence_id!r}",
            )
        require(
            isinstance(self.note, str),
            "note must be a string",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_order": self.step_order,
            "action": self.action,
            "actor": self.actor,
            "occurred_at": self.occurred_at,
            "evidence_id": self.evidence_id,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceStep:
        raw_eid = data.get("evidence_id")
        return cls(
            step_order=int(data["step_order"]),
            action=data["action"],
            actor=data["actor"],
            occurred_at=data["occurred_at"],
            evidence_id=EvidenceId(raw_eid) if raw_eid else None,
            note=data.get("note", ""),
        )


@dataclass(frozen=True)
class Provenance:
    provenance_id: ProvenanceId
    fact_id: FactId
    entity_id: EntityId
    decision_chain: tuple[ProvenanceStep, ...]
    summary: str
    created_at: str

    def __post_init__(self) -> None:
        require(
            is_valid_provenance_id(self.provenance_id),
            f"invalid provenance_id: {self.provenance_id!r}",
        )
        require(
            is_valid_fact_id(self.fact_id),
            f"invalid fact_id: {self.fact_id!r}",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"invalid entity_id: {self.entity_id!r}",
        )
        require(
            isinstance(self.decision_chain, tuple) and len(self.decision_chain) > 0,
            "decision_chain must be a non-empty tuple of ProvenanceStep",
        )
        require(
            all(isinstance(s, ProvenanceStep) for s in self.decision_chain),
            "all items in decision_chain must be ProvenanceStep instances",
        )
        require(
            isinstance(self.summary, str) and bool(self.summary.strip()),
            "summary must be a non-empty string",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        self._require_ordered_chain()

    def _require_ordered_chain(self) -> None:
        orders = [s.step_order for s in self.decision_chain]
        require(
            orders == sorted(orders),
            f"decision_chain steps must be ordered by step_order, got {orders}",
        )
        require(
            len(orders) == len(set(orders)),
            f"decision_chain step_order values must be unique, got {orders}",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "fact_id": self.fact_id,
            "entity_id": self.entity_id,
            "decision_chain": [s.to_dict() for s in self.decision_chain],
            "summary": self.summary,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        return cls(
            provenance_id=ProvenanceId(data["provenance_id"]),
            fact_id=FactId(data["fact_id"]),
            entity_id=EntityId(data["entity_id"]),
            decision_chain=tuple(
                ProvenanceStep.from_dict(s) for s in data["decision_chain"]
            ),
            summary=data["summary"],
            created_at=data["created_at"],
        )

    @classmethod
    def create(
        cls,
        fact_id: str,
        entity_id: str,
        decision_chain: list[ProvenanceStep],
        summary: str,
    ) -> Provenance:
        require(is_valid_fact_id(fact_id), f"invalid fact_id: {fact_id!r}")
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        require(
            isinstance(decision_chain, list) and len(decision_chain) > 0,
            "decision_chain must be a non-empty list of ProvenanceStep",
        )
        require(
            isinstance(summary, str) and bool(summary.strip()),
            "summary must be a non-empty string",
        )
        return cls(
            provenance_id=generate_provenance_id(),
            fact_id=FactId(fact_id),
            entity_id=EntityId(entity_id),
            decision_chain=tuple(decision_chain),
            summary=summary,
            created_at=utcnow_iso(),
        )
