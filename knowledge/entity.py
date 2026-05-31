from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_entity_id,
    is_valid_entity_id,
)
from core.time import is_valid_timestamp, parse_timestamp, utcnow_iso
from core.types import EntityId


class EntityStatus(StrEnum):
    ACTIVE = "active"
    MERGED = "merged"
    ARCHIVED = "archived"


class EntityType:
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    DOCUMENT = "document"


@dataclass(frozen=True)
class Entity:
    entity_id: EntityId
    entity_type: str
    display_name: str
    status: EntityStatus
    created_at: str
    updated_at: str
    primary_language: str | None = field(default=None)
    merged_into: EntityId | None = field(default=None)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
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
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        require(
            is_valid_timestamp(self.updated_at),
            f"invalid updated_at: {self.updated_at!r}",
        )
        require(
            parse_timestamp(self.updated_at) >= parse_timestamp(self.created_at),
            "updated_at cannot be earlier than created_at",
        )
        if self.primary_language is not None:
            require(
                isinstance(self.primary_language, str)
                and bool(self.primary_language.strip()),
                "primary_language must be a non-empty string when provided",
            )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )
        if self.status is EntityStatus.MERGED:
            require(
                self.merged_into is not None,
                "merged_into required when status is MERGED",
            )
            assert self.merged_into is not None
            require(
                is_valid_entity_id(self.merged_into),
                f"invalid merged_into: {self.merged_into!r}",
            )
            require(
                self.merged_into != self.entity_id,
                "entity cannot be merged into itself",
            )
        else:
            require(
                self.merged_into is None,
                f"merged_into must be None when status is {self.status!r}",
            )

    def rename(self, new_display_name: str) -> Entity:
        require(
            self.status is EntityStatus.ACTIVE,
            f"only ACTIVE entities can be renamed, got {self.status!r}",
        )
        require(
            isinstance(new_display_name, str) and bool(new_display_name.strip()),
            "new_display_name must be a non-empty string",
        )
        return Entity(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            display_name=new_display_name,
            status=self.status,
            created_at=self.created_at,
            updated_at=utcnow_iso(),
            primary_language=self.primary_language,
            merged_into=None,
            metadata=dict(self.metadata),
        )

    def merge_into(self, target_id: EntityId) -> Entity:
        require(
            self.status is EntityStatus.ACTIVE,
            f"only ACTIVE entities can be merged, got {self.status!r}",
        )
        require(
            is_valid_entity_id(target_id),
            f"invalid target_id: {target_id!r}",
        )
        require(
            target_id != self.entity_id,
            "entity cannot be merged into itself",
        )
        return Entity(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            display_name=self.display_name,
            status=EntityStatus.MERGED,
            created_at=self.created_at,
            updated_at=utcnow_iso(),
            primary_language=self.primary_language,
            merged_into=target_id,
            metadata=dict(self.metadata),
        )

    def archive(self) -> Entity:
        require(
            self.status is EntityStatus.ACTIVE,
            f"only ACTIVE entities can be archived, got {self.status!r}",
        )
        return Entity(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            display_name=self.display_name,
            status=EntityStatus.ARCHIVED,
            created_at=self.created_at,
            updated_at=utcnow_iso(),
            primary_language=self.primary_language,
            merged_into=None,
            metadata=dict(self.metadata),
        )

    def with_primary_language(self, language: str) -> Entity:
        require(
            self.status is EntityStatus.ACTIVE,
            f"only ACTIVE entities can be updated, got {self.status!r}",
        )
        require(
            isinstance(language, str) and bool(language.strip()),
            "language must be a non-empty string",
        )
        return Entity(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            display_name=self.display_name,
            status=self.status,
            created_at=self.created_at,
            updated_at=utcnow_iso(),
            primary_language=language,
            merged_into=None,
            metadata=dict(self.metadata),
        )

    def with_metadata(self, metadata: dict[str, Any]) -> Entity:
        require(
            self.status is EntityStatus.ACTIVE,
            f"only ACTIVE entities can be updated, got {self.status!r}",
        )
        require(
            isinstance(metadata, dict),
            "metadata must be a dictionary",
        )
        return Entity(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            display_name=self.display_name,
            status=self.status,
            created_at=self.created_at,
            updated_at=utcnow_iso(),
            primary_language=self.primary_language,
            merged_into=None,
            metadata=dict(metadata),
        )

    @property
    def is_active(self) -> bool:
        return self.status is EntityStatus.ACTIVE

    @property
    def is_terminal(self) -> bool:
        return self.status in (EntityStatus.MERGED, EntityStatus.ARCHIVED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "display_name": self.display_name,
            "status": str(self.status),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "primary_language": self.primary_language,
            "merged_into": self.merged_into,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        return cls(
            entity_id=EntityId(data["entity_id"]),
            entity_type=data["entity_type"],
            display_name=data["display_name"],
            status=EntityStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            primary_language=data.get("primary_language"),
            merged_into=(
                EntityId(data["merged_into"]) if data.get("merged_into") else None
            ),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        entity_type: str,
        display_name: str,
        primary_language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        require(
            isinstance(entity_type, str) and bool(entity_type.strip()),
            "entity_type must be a non-empty string",
        )
        require(
            isinstance(display_name, str) and bool(display_name.strip()),
            "display_name must be a non-empty string",
        )
        if primary_language is not None:
            require(
                isinstance(primary_language, str) and bool(primary_language.strip()),
                "primary_language must be a non-empty string when provided",
            )
        now = utcnow_iso()
        return cls(
            entity_id=generate_entity_id(),
            entity_type=entity_type,
            display_name=display_name,
            status=EntityStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            primary_language=primary_language,
            merged_into=None,
            metadata=dict(metadata) if metadata else {},
        )
