from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_profile_id,
    is_valid_entity_id,
    is_valid_fact_id,
    is_valid_profile_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import EntityId, FactId, ProfileId
from knowledge.fact import CanonicalValue


@dataclass(frozen=True)
class ProfileField:
    field_name: str
    value: CanonicalValue
    display_value: str
    confidence: float
    fact_id: FactId
    sourced_at: str

    def __post_init__(self) -> None:
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
            is_valid_fact_id(self.fact_id),
            f"invalid fact_id: {self.fact_id!r}",
        )
        require(
            is_valid_timestamp(self.sourced_at),
            f"invalid sourced_at: {self.sourced_at!r}",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "display_value": self.display_value,
            "confidence": self.confidence,
            "fact_id": self.fact_id,
            "sourced_at": self.sourced_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileField:
        return cls(
            field_name=data["field_name"],
            value=data["value"],
            display_value=data["display_value"],
            confidence=float(data["confidence"]),
            fact_id=FactId(data["fact_id"]),
            sourced_at=data["sourced_at"],
        )


@dataclass(frozen=True)
class Profile:
    profile_id: ProfileId
    entity_id: EntityId
    entity_type: str
    display_name: str
    fields: Mapping[str, ProfileField]  # runtime: MappingProxyType
    completeness: float
    computed_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_profile_id(self.profile_id),
            f"invalid profile_id: {self.profile_id!r}",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"invalid entity_id: {self.entity_id!r}",
        )
        require(
            isinstance(self.entity_type, str) and bool(self.entity_type.strip()),
            "entity_type must be a non-empty string",
        )
        require(
            isinstance(self.display_name, str) and bool(self.display_name.strip()),
            "display_name must be a non-empty string",
        )
        require(
            isinstance(self.fields, MappingProxyType),
            "fields must be a MappingProxyType",
        )
        require(
            all(
                isinstance(k, str) and bool(k.strip()) and isinstance(v, ProfileField)
                for k, v in self.fields.items()
            ),
            "fields must map non-empty strings to ProfileField instances",
        )
        require(
            all(k == v.field_name for k, v in self.fields.items()),
            "each fields key must match its ProfileField.field_name",
        )
        require(
            0.0 <= self.completeness <= 1.0,
            f"completeness must be in [0.0, 1.0], got {self.completeness}",
        )
        require(
            is_valid_timestamp(self.computed_at),
            f"invalid computed_at: {self.computed_at!r}",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    def get_field(self, field_name: str) -> ProfileField | None:
        return self.fields.get(field_name)

    def has_field(self, field_name: str) -> bool:
        return field_name in self.fields

    def field_names(self) -> frozenset[str]:
        return frozenset(self.fields.keys())

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "display_name": self.display_name,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "completeness": self.completeness,
            "computed_at": self.computed_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        return cls(
            profile_id=ProfileId(data["profile_id"]),
            entity_id=EntityId(data["entity_id"]),
            entity_type=data["entity_type"],
            display_name=data["display_name"],
            fields=MappingProxyType(
                {k: ProfileField.from_dict(v) for k, v in data["fields"].items()}
            ),
            completeness=float(data["completeness"]),
            computed_at=data["computed_at"],
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def create(
        cls,
        entity_id: EntityId,
        entity_type: str,
        display_name: str,
        fields: dict[str, ProfileField],
        completeness: float,
        metadata: dict[str, Any] | None = None,
    ) -> Profile:
        return cls(
            profile_id=generate_profile_id(),
            entity_id=entity_id,
            entity_type=entity_type,
            display_name=display_name,
            fields=MappingProxyType(dict(fields)),
            completeness=completeness,
            computed_at=utcnow_iso(),
            metadata=dict(metadata) if metadata else {},
        )
