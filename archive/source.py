from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from archive.document import Document
from core.guards import require
from core.identifiers import (
    generate_source_id,
    is_valid_document_id,
    is_valid_entity_id,
    is_valid_source_id,
)
from core.time import utcnow_iso
from core.types import DocumentId, EntityId, SourceId


class SourceType(StrEnum):
    DOCUMENT = "document"
    USER_INPUT = "user_input"
    IMPORT = "import"


@dataclass(frozen=True)
class Source:
    source_id: SourceId
    entity_id: EntityId
    source_type: SourceType
    created_at: str

    document_id: DocumentId | None = field(default=None)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_source_id(self.source_id),
            f"invalid source_id: {self.source_id!r}",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"invalid entity_id: {self.entity_id!r}",
        )

        if self.source_type is SourceType.DOCUMENT:
            require(
                self.document_id is not None,
                "source_type DOCUMENT requires a document_id",
            )
            assert self.document_id is not None  # narrow for mypy
            require(
                is_valid_document_id(self.document_id),
                f"invalid document_id: {self.document_id!r}",
            )
        else:
            require(
                self.document_id is None,
                f"source_type {self.source_type} must not carry a document_id",
            )

    @property
    def is_document_backed(self) -> bool:
        return self.source_type is SourceType.DOCUMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "entity_id": self.entity_id,
            "source_type": str(self.source_type),
            "created_at": self.created_at,
            "document_id": self.document_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Source:
        return cls(
            source_id=SourceId(data["source_id"]),
            entity_id=EntityId(data["entity_id"]),
            source_type=SourceType(data["source_type"]),
            created_at=data["created_at"],
            document_id=(
                DocumentId(data["document_id"]) if data.get("document_id") else None
            ),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_document(
        cls,
        entity_id: str,
        document: Document,
        metadata: dict[str, Any] | None = None,
    ) -> Source:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        require(
            document.entity_id == entity_id,
            f"document belongs to entity {document.entity_id!r}, not {entity_id!r}",
        )
        return cls(
            source_id=generate_source_id(),
            entity_id=EntityId(entity_id),
            source_type=SourceType.DOCUMENT,
            created_at=utcnow_iso(),
            document_id=document.document_id,
            metadata=dict(metadata) if metadata else {},
        )

    @classmethod
    def from_user_input(
        cls,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Source:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        return cls(
            source_id=generate_source_id(),
            entity_id=EntityId(entity_id),
            source_type=SourceType.USER_INPUT,
            created_at=utcnow_iso(),
            document_id=None,
            metadata=dict(metadata) if metadata else {},
        )

    @classmethod
    def from_import(
        cls,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Source:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        return cls(
            source_id=generate_source_id(),
            entity_id=EntityId(entity_id),
            source_type=SourceType.IMPORT,
            created_at=utcnow_iso(),
            document_id=None,
            metadata=dict(metadata) if metadata else {},
        )
