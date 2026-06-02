from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import generate_ocr_word_id, is_valid_ocr_word_id
from core.types import ConfidenceScore, Metadata, OcrWordId
from processing.ocr.bounding_box import BoundingBox

_MIN_CONFIDENCE: ConfidenceScore = 0.0
_MAX_CONFIDENCE: ConfidenceScore = 1.0


@dataclass(frozen=True)
class OcrWord:
    ocr_word_id: OcrWordId
    text: str
    confidence: ConfidenceScore
    bounding_box: BoundingBox
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.ocr_word_id, str), "ocr_word_id must be a str")
        require(
            is_valid_ocr_word_id(self.ocr_word_id),
            "ocr_word_id must be a valid OcrWordId",
        )
        require(isinstance(self.text, str), "text must be a str")
        require(bool(self.text.strip()), "text must not be empty")
        require(
            isinstance(self.confidence, (int, float)), "confidence must be a number"
        )
        require(
            _MIN_CONFIDENCE <= self.confidence <= _MAX_CONFIDENCE,
            f"confidence must be in [{_MIN_CONFIDENCE}, {_MAX_CONFIDENCE}]",
        )
        require(
            isinstance(self.bounding_box, BoundingBox),
            "bounding_box must be a BoundingBox",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        text: str,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        metadata: Metadata | None = None,
    ) -> OcrWord:
        return cls(
            ocr_word_id=generate_ocr_word_id(),
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        ocr_word_id: OcrWordId,
        text: str,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        metadata: Metadata | None = None,
    ) -> OcrWord:
        return cls(
            ocr_word_id=ocr_word_id,
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def char_count(self) -> int:
        return len(self.text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ocr_word_id": self.ocr_word_id,
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OcrWord:
        return cls(
            ocr_word_id=data["ocr_word_id"],
            text=data["text"],
            confidence=data["confidence"],
            bounding_box=BoundingBox.from_dict(data["bounding_box"]),
            metadata=data.get("metadata", {}),
        )
