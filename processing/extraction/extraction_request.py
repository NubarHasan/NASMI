from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_extraction_request_id,
    is_valid_source_id,
)
from core.types import (
    ExtractionRequestId,
    SourceId,
)
from processing.extraction.extractable_content import ExtractableContent


@dataclass(frozen=True)
class ExtractionRequest:
    extraction_request_id: ExtractionRequestId
    source_id: SourceId
    extractable_content: ExtractableContent
    requested_fact_types: tuple[str, ...]
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_source_id(self.source_id),
            f"Invalid SourceId: [{self.source_id}]",
        )
        require(
            isinstance(self.extractable_content, ExtractableContent),
            "extractable_content must be an ExtractableContent instance",
        )
        require(
            isinstance(self.requested_fact_types, tuple),
            "requested_fact_types must be a tuple",
        )
        require(
            len(self.requested_fact_types) > 0,
            "requested_fact_types must not be empty",
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
    def language(self) -> str:
        return self.extractable_content.language

    @property
    def is_low_quality(self) -> bool:
        return self.extractable_content.is_low_quality

    @classmethod
    def create(
        cls,
        source_id: SourceId,
        extractable_content: ExtractableContent,
        requested_fact_types: tuple[str, ...],
        created_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionRequest:
        return cls(
            extraction_request_id=generate_extraction_request_id(),
            source_id=source_id,
            extractable_content=extractable_content,
            requested_fact_types=requested_fact_types,
            created_at=created_at,
            metadata=dict(metadata) if metadata is not None else {},
        )
