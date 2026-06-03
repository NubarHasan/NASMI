from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import generate_extraction_request_id
from core.time import utcnow
from core.types import (
    EntityId,
    ExtractionRequestId,
)
from processing.extraction.extractable_content import ExtractableContent


@dataclass(frozen=True)
class ExtractionRequest:
    extraction_request_id: ExtractionRequestId
    entity_id: EntityId
    content: ExtractableContent
    requested_fact_types: tuple[str, ...]
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            isinstance(self.entity_id, EntityId),
            "entity_id must be an EntityId instance",
        )
        require(
            isinstance(self.content, ExtractableContent),
            "content must be an ExtractableContent instance",
        )
        require(
            isinstance(self.requested_fact_types, tuple),
            "requested_fact_types must be a tuple",
        )
        require(
            all(
                isinstance(v, str) and bool(v.strip())
                for v in self.requested_fact_types
            ),
            "requested_fact_types must contain non-empty string values",
        )
        require(
            isinstance(self.created_at, datetime),
            "created_at must be a datetime instance",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    @property
    def source_id(self):
        return self.content.source_id

    @property
    def document_id(self):
        return self.content.document_id

    @property
    def language(self) -> str:
        return self.content.language

    @property
    def is_low_quality(self) -> bool:
        return self.content.is_low_quality

    @classmethod
    def create(
        cls,
        entity_id: EntityId,
        content: ExtractableContent,
        requested_fact_types: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionRequest:
        return cls(
            extraction_request_id=generate_extraction_request_id(),
            entity_id=entity_id,
            content=content,
            requested_fact_types=requested_fact_types,
            created_at=utcnow(),
            metadata=dict(metadata) if metadata is not None else {},
        )
