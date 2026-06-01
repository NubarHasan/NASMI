from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.types import ConfidenceScore, LanguageCode, PageCount


@dataclass(frozen=True)
class ExtractableContent:
    raw_text: str
    language: LanguageCode
    page_count: PageCount
    ocr_confidence: ConfidenceScore
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            bool(self.raw_text.strip()),
            "raw_text must not be empty",
        )
        require(
            bool(self.language.strip()),
            "language must not be empty",
        )
        require(
            self.page_count >= 1,
            f"page_count must be >= 1, got [{self.page_count}]",
        )
        require(
            0.0 <= self.ocr_confidence <= 1.0,
            f"ocr_confidence must be between 0.0 and 1.0, got [{self.ocr_confidence}]",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    @property
    def is_low_quality(self) -> bool:
        return self.ocr_confidence < 0.5

    @property
    def char_count(self) -> int:
        return len(self.raw_text)

    @classmethod
    def create(
        cls,
        raw_text: str,
        language: LanguageCode,
        page_count: PageCount,
        ocr_confidence: ConfidenceScore,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractableContent:
        return cls(
            raw_text=raw_text,
            language=language,
            page_count=page_count,
            ocr_confidence=ocr_confidence,
            metadata=dict(metadata) if metadata is not None else {},
        )
