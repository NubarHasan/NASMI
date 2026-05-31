from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import generate_fact_id, is_valid_entity_id, is_valid_fact_id
from core.time import is_valid_timestamp, utcnow_iso
from core.types import EntityId, FactId

CanonicalValue = str | int | float | bool | date | datetime | None


class ValueType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    NULL = "null"


class FactStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def _infer_value_type(value: CanonicalValue) -> ValueType:
    if value is None:
        return ValueType.NULL
    if isinstance(value, bool):
        return ValueType.BOOLEAN
    if isinstance(value, int):
        return ValueType.INTEGER
    if isinstance(value, float):
        return ValueType.FLOAT
    if isinstance(value, datetime):
        return ValueType.DATETIME
    if isinstance(value, date):
        return ValueType.DATE
    return ValueType.STRING


def _serialize_value(value: CanonicalValue, vtype: ValueType) -> str | None:
    if value is None:
        return None
    if vtype is ValueType.DATETIME:
        return value.isoformat()  # type: ignore[union-attr]
    if vtype is ValueType.DATE:
        return value.isoformat()  # type: ignore[union-attr]
    return str(value)


def _deserialize_value(raw: str | None, vtype: ValueType) -> CanonicalValue:
    if raw is None or vtype is ValueType.NULL:
        return None
    if vtype is ValueType.BOOLEAN:
        return raw.lower() == "true"
    if vtype is ValueType.INTEGER:
        return int(raw)
    if vtype is ValueType.FLOAT:
        return float(raw)
    if vtype is ValueType.DATETIME:
        return datetime.fromisoformat(raw)
    if vtype is ValueType.DATE:
        return date.fromisoformat(raw)
    return raw


@dataclass(frozen=True)
class Fact:
    fact_id: FactId
    entity_id: EntityId
    field_name: str
    canonical_value: CanonicalValue
    display_value: str
    value_type: ValueType
    confidence: float
    status: FactStatus
    source_stage: str
    created_at: str
    accepted_at: str | None = field(default=None)
    accepted_by: str | None = field(default=None)
    superseded_by: FactId | None = field(default=None)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_fact_id(self.fact_id),
            f"invalid fact_id: {self.fact_id!r}",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"invalid entity_id: {self.entity_id!r}",
        )
        require(
            isinstance(self.field_name, str) and bool(self.field_name.strip()),
            "field_name must be a non-empty string",
        )
        require(
            isinstance(self.display_value, str) and bool(self.display_value.strip()),
            "display_value must be a non-empty string",
        )
        require(
            0.0 <= self.confidence <= 1.0,
            f"confidence must be in [0.0, 1.0], got {self.confidence}",
        )
        require(
            isinstance(self.source_stage, str) and bool(self.source_stage.strip()),
            "source_stage must be a non-empty string",
        )
        require(
            _infer_value_type(self.canonical_value) == self.value_type,
            f"value_type mismatch: declared {self.value_type!r} "
            f"but canonical_value is {type(self.canonical_value).__name__}",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        if self.accepted_at is not None:
            require(
                is_valid_timestamp(self.accepted_at),
                f"invalid accepted_at: {self.accepted_at!r}",
            )
        if self.status is FactStatus.ACCEPTED:
            require(
                self.accepted_at is not None,
                "accepted_at required when status is ACCEPTED",
            )
        if self.status is FactStatus.SUPERSEDED:
            require(
                self.superseded_by is not None,
                "superseded_by required when status is SUPERSEDED",
            )
            assert self.superseded_by is not None
            require(
                is_valid_fact_id(self.superseded_by),
                f"invalid superseded_by: {self.superseded_by!r}",
            )

    def accept(self, accepted_by: str) -> Fact:
        require(
            self.status is FactStatus.PENDING,
            f"only PENDING facts can be accepted, got {self.status!r}",
        )
        require(
            isinstance(accepted_by, str) and bool(accepted_by.strip()),
            "accepted_by must be a non-empty string",
        )
        return Fact(
            fact_id=self.fact_id,
            entity_id=self.entity_id,
            field_name=self.field_name,
            canonical_value=self.canonical_value,
            display_value=self.display_value,
            value_type=self.value_type,
            confidence=self.confidence,
            status=FactStatus.ACCEPTED,
            source_stage=self.source_stage,
            created_at=self.created_at,
            accepted_at=utcnow_iso(),
            accepted_by=accepted_by,
            superseded_by=None,
            metadata=dict(self.metadata),
        )

    def reject(self) -> Fact:
        require(
            self.status is FactStatus.PENDING,
            f"only PENDING facts can be rejected, got {self.status!r}",
        )
        return Fact(
            fact_id=self.fact_id,
            entity_id=self.entity_id,
            field_name=self.field_name,
            canonical_value=self.canonical_value,
            display_value=self.display_value,
            value_type=self.value_type,
            confidence=self.confidence,
            status=FactStatus.REJECTED,
            source_stage=self.source_stage,
            created_at=self.created_at,
            accepted_at=None,
            accepted_by=None,
            superseded_by=None,
            metadata=dict(self.metadata),
        )

    def supersede(self, new_fact_id: FactId) -> Fact:
        require(
            self.status is FactStatus.ACCEPTED,
            f"only ACCEPTED facts can be superseded, got {self.status!r}",
        )
        require(is_valid_fact_id(new_fact_id), f"invalid new_fact_id: {new_fact_id!r}")
        return Fact(
            fact_id=self.fact_id,
            entity_id=self.entity_id,
            field_name=self.field_name,
            canonical_value=self.canonical_value,
            display_value=self.display_value,
            value_type=self.value_type,
            confidence=self.confidence,
            status=FactStatus.SUPERSEDED,
            source_stage=self.source_stage,
            created_at=self.created_at,
            accepted_at=self.accepted_at,
            accepted_by=self.accepted_by,
            superseded_by=new_fact_id,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "canonical_value": _serialize_value(self.canonical_value, self.value_type),
            "display_value": self.display_value,
            "value_type": str(self.value_type),
            "confidence": self.confidence,
            "status": str(self.status),
            "source_stage": self.source_stage,
            "created_at": self.created_at,
            "accepted_at": self.accepted_at,
            "accepted_by": self.accepted_by,
            "superseded_by": self.superseded_by,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fact:
        vtype = ValueType(data["value_type"])
        return cls(
            fact_id=FactId(data["fact_id"]),
            entity_id=EntityId(data["entity_id"]),
            field_name=data["field_name"],
            canonical_value=_deserialize_value(data.get("canonical_value"), vtype),
            display_value=data["display_value"],
            value_type=vtype,
            confidence=float(data["confidence"]),
            status=FactStatus(data["status"]),
            source_stage=data["source_stage"],
            created_at=data["created_at"],
            accepted_at=data.get("accepted_at"),
            accepted_by=data.get("accepted_by"),
            superseded_by=(
                FactId(data["superseded_by"]) if data.get("superseded_by") else None
            ),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        entity_id: str,
        field_name: str,
        canonical_value: CanonicalValue,
        display_value: str,
        source_stage: str,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> Fact:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        require(
            isinstance(field_name, str) and bool(field_name.strip()),
            "field_name must be a non-empty string",
        )
        require(
            isinstance(source_stage, str) and bool(source_stage.strip()),
            "source_stage must be a non-empty string",
        )
        require(
            0.0 <= confidence <= 1.0,
            f"confidence must be in [0.0, 1.0], got {confidence}",
        )
        vtype = _infer_value_type(canonical_value)
        return cls(
            fact_id=generate_fact_id(),
            entity_id=EntityId(entity_id),
            field_name=field_name,
            canonical_value=canonical_value,
            display_value=display_value,
            value_type=vtype,
            confidence=confidence,
            status=FactStatus.PENDING,
            source_stage=source_stage,
            created_at=utcnow_iso(),
            accepted_at=None,
            accepted_by=None,
            superseded_by=None,
            metadata=dict(metadata) if metadata else {},
        )
