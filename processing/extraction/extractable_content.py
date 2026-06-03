from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.types import (
    DocumentId,
    LanguageCode,
    PageNumber,
    SourceId,
)
from processing.extraction.spatial_data import (
    ExtractableSpan,
    ExtractableSpanType,
    ExtractableSpatialData,
)


@dataclass(frozen=True)
class ExtractableContent:
    source_id: SourceId
    document_id: DocumentId
    document_type: str | None
    language: LanguageCode | None
    raw_text: str
    normalized_text: str
    spatial_data: ExtractableSpatialData | None
    extraction_hints: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            isinstance(self.source_id, str) and bool(self.source_id.strip()),
            "source_id must be a non-empty string",
        )
        require(
            isinstance(self.document_id, str) and bool(self.document_id.strip()),
            "document_id must be a non-empty string",
        )
        require(
            self.document_type is None
            or (
                isinstance(self.document_type, str) and bool(self.document_type.strip())
            ),
            "document_type must be a non-empty string or None",
        )
        require(
            self.language is None or isinstance(self.language, str),
            "language must be a str or None",
        )
        require(isinstance(self.raw_text, str), "raw_text must be a string")
        require(
            isinstance(self.normalized_text, str),
            "normalized_text must be a string",
        )
        require(
            self.spatial_data is None
            or isinstance(self.spatial_data, ExtractableSpatialData),
            "spatial_data must be an ExtractableSpatialData or None",
        )
        require(
            isinstance(self.extraction_hints, tuple),
            "extraction_hints must be a tuple",
        )
        require(
            all(isinstance(h, str) and bool(h.strip()) for h in self.extraction_hints),
            "extraction_hints must contain non-empty strings",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @property
    def has_text(self) -> bool:
        return bool(self.normalized_text.strip())

    @property
    def char_count(self) -> int:
        return len(self.normalized_text)

    @property
    def word_count(self) -> int:
        return len(self.normalized_text.split())

    @property
    def is_german(self) -> bool:
        return self.language == "de"

    @property
    def is_document_type_known(self) -> bool:
        return self.document_type is not None

    @property
    def page_count(self) -> int:
        if self.spatial_data is None:
            return 0
        return self.spatial_data.page_count

    @property
    def mean_confidence(self) -> float:
        if self.spatial_data is None:
            return 0.0
        return self.spatial_data.mean_confidence

    @property
    def is_low_quality(self) -> bool:
        if self.spatial_data is None:
            return True
        return self.spatial_data.is_low_quality

    @property
    def has_spatial_data(self) -> bool:
        return self.spatial_data is not None

    @property
    def all_spans(self) -> tuple[ExtractableSpan, ...]:
        if self.spatial_data is None:
            return ()
        return self.spatial_data.spans

    def spans_by_type(
        self, span_type: ExtractableSpanType
    ) -> tuple[ExtractableSpan, ...]:
        if self.spatial_data is None:
            return ()
        return self.spatial_data.spans_by_type(span_type)

    def spans_for_page(self, page_number: PageNumber) -> tuple[ExtractableSpan, ...]:
        if self.spatial_data is None:
            return ()
        return self.spatial_data.spans_for_page(page_number)

    def find_by_text(
        self,
        query: str,
        *,
        case_sensitive: bool = False,
    ) -> tuple[ExtractableSpan, ...]:
        if self.spatial_data is None:
            return ()
        return self.spatial_data.find_by_text(query, case_sensitive=case_sensitive)

    def with_document_type(self, document_type: str) -> ExtractableContent:
        require(
            isinstance(document_type, str) and bool(document_type.strip()),
            "document_type must be a non-empty string",
        )
        return ExtractableContent(
            source_id=self.source_id,
            document_id=self.document_id,
            document_type=document_type,
            language=self.language,
            raw_text=self.raw_text,
            normalized_text=self.normalized_text,
            spatial_data=self.spatial_data,
            extraction_hints=self.extraction_hints,
            metadata=dict(self.metadata),
        )

    def with_hint(self, hint: str) -> ExtractableContent:
        require(
            isinstance(hint, str) and bool(hint.strip()),
            "hint must be a non-empty string",
        )
        return ExtractableContent(
            source_id=self.source_id,
            document_id=self.document_id,
            document_type=self.document_type,
            language=self.language,
            raw_text=self.raw_text,
            normalized_text=self.normalized_text,
            spatial_data=self.spatial_data,
            extraction_hints=(*self.extraction_hints, hint),
            metadata=dict(self.metadata),
        )

    def with_metadata(self, key: str, value: Any) -> ExtractableContent:
        require(
            isinstance(key, str) and bool(key.strip()),
            "key must be a non-empty string",
        )
        return ExtractableContent(
            source_id=self.source_id,
            document_id=self.document_id,
            document_type=self.document_type,
            language=self.language,
            raw_text=self.raw_text,
            normalized_text=self.normalized_text,
            spatial_data=self.spatial_data,
            extraction_hints=self.extraction_hints,
            metadata={**self.metadata, key: value},
        )

    def with_normalized_text(self, normalized_text: str) -> ExtractableContent:
        require(isinstance(normalized_text, str), "normalized_text must be a string")
        return ExtractableContent(
            source_id=self.source_id,
            document_id=self.document_id,
            document_type=self.document_type,
            language=self.language,
            raw_text=self.raw_text,
            normalized_text=normalized_text,
            spatial_data=self.spatial_data,
            extraction_hints=self.extraction_hints,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "language": self.language,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "spatial_data": (
                self.spatial_data.to_dict() if self.spatial_data is not None else None
            ),
            "extraction_hints": list(self.extraction_hints),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractableContent:
        raw_spatial = data.get("spatial_data")
        return cls(
            source_id=SourceId(data["source_id"]),
            document_id=DocumentId(data["document_id"]),
            document_type=data.get("document_type"),
            language=data.get("language"),
            raw_text=data.get("raw_text", ""),
            normalized_text=data.get("normalized_text", ""),
            spatial_data=(
                ExtractableSpatialData.from_dict(raw_spatial)
                if raw_spatial is not None
                else None
            ),
            extraction_hints=tuple(data.get("extraction_hints") or []),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_spatial_data(
        cls,
        spatial_data: ExtractableSpatialData,
        *,
        document_type: str | None = None,
        language: LanguageCode | None = None,
        extraction_hints: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ExtractableContent:
        return cls(
            source_id=spatial_data.source_id,
            document_id=spatial_data.document_id,
            document_type=document_type,
            language=language,
            raw_text=spatial_data.reconstructed_text,
            normalized_text=spatial_data.reconstructed_text.strip(),
            spatial_data=spatial_data,
            extraction_hints=extraction_hints,
            metadata=dict(metadata) if metadata is not None else {},
        )
