from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_evidence_id,
    is_valid_entity_id,
    is_valid_evidence_id,
    is_valid_source_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import EntityId, EvidenceId, SourceId


@dataclass(frozen=True)
class Evidence:
    evidence_id: EvidenceId
    source_id: SourceId
    entity_id: EntityId
    field_name: str
    raw_value: str
    extraction_method: str
    confidence: float
    created_at: str
    location: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_evidence_id(self.evidence_id),
            f"invalid evidence_id: {self.evidence_id!r}",
        )
        require(
            is_valid_source_id(self.source_id),
            f"invalid source_id: {self.source_id!r}",
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
            isinstance(self.raw_value, str) and bool(self.raw_value.strip()),
            "raw_value must be a non-empty string",
        )
        require(
            isinstance(self.extraction_method, str)
            and bool(self.extraction_method.strip()),
            "extraction_method must be a non-empty string",
        )
        require(
            0.0 <= self.confidence <= 1.0,
            f"confidence must be in [0.0, 1.0], got {self.confidence}",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        require(
            isinstance(self.location, dict),
            "location must be a dictionary",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "raw_value": self.raw_value,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "location": dict(self.location),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Evidence:
        return cls(
            evidence_id=EvidenceId(data["evidence_id"]),
            source_id=SourceId(data["source_id"]),
            entity_id=EntityId(data["entity_id"]),
            field_name=data["field_name"],
            raw_value=data["raw_value"],
            extraction_method=data["extraction_method"],
            confidence=float(data["confidence"]),
            created_at=data["created_at"],
            location=data.get("location", {}),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        source_id: str,
        entity_id: str,
        field_name: str,
        raw_value: str,
        extraction_method: str,
        confidence: float = 1.0,
        location: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Evidence:
        require(is_valid_source_id(source_id), f"invalid source_id: {source_id!r}")
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        require(
            isinstance(field_name, str) and bool(field_name.strip()),
            "field_name must be a non-empty string",
        )
        require(
            isinstance(raw_value, str) and bool(raw_value.strip()),
            "raw_value must be a non-empty string",
        )
        require(
            isinstance(extraction_method, str) and bool(extraction_method.strip()),
            "extraction_method must be a non-empty string",
        )
        require(
            0.0 <= confidence <= 1.0,
            f"confidence must be in [0.0, 1.0], got {confidence}",
        )
        return cls(
            evidence_id=generate_evidence_id(),
            source_id=SourceId(source_id),
            entity_id=EntityId(entity_id),
            field_name=field_name,
            raw_value=raw_value,
            extraction_method=extraction_method,
            confidence=confidence,
            created_at=utcnow_iso(),
            location=dict(location) if location else {},
            metadata=dict(metadata) if metadata else {},
        )
