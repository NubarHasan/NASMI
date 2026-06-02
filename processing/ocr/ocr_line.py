from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import generate_ocr_line_id, is_valid_ocr_line_id
from core.types import ConfidenceScore, Metadata, OcrLineId
from processing.ocr.bounding_box import BoundingBox
from processing.ocr.ocr_word import OcrWord

_MIN_CONFIDENCE: ConfidenceScore = 0.0
_MAX_CONFIDENCE: ConfidenceScore = 1.0


@dataclass(frozen=True)
class OcrLine:
    ocr_line_id: OcrLineId
    text: str
    confidence: ConfidenceScore
    bounding_box: BoundingBox
    words: tuple[OcrWord, ...]
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.ocr_line_id, str), "ocr_line_id must be a str")
        require(
            is_valid_ocr_line_id(self.ocr_line_id),
            "ocr_line_id must be a valid OcrLineId",
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
        require(isinstance(self.words, tuple), "words must be a tuple")
        require(
            all(isinstance(w, OcrWord) for w in self.words),
            "every element of words must be an OcrWord",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        text: str,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        words: list[OcrWord] | tuple[OcrWord, ...] | None = None,
        metadata: Metadata | None = None,
    ) -> OcrLine:
        return cls(
            ocr_line_id=generate_ocr_line_id(),
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            words=tuple(words) if words is not None else (),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        ocr_line_id: OcrLineId,
        text: str,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        words: list[OcrWord] | tuple[OcrWord, ...],
        metadata: Metadata | None = None,
    ) -> OcrLine:
        return cls(
            ocr_line_id=ocr_line_id,
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            words=tuple(words),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def has_words(self) -> bool:
        return len(self.words) > 0

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def reconstructed_text(self) -> str:
        if not self.has_words:
            return self.text
        return " ".join(w.text for w in self.words)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        if not self.has_words:
            return self.confidence
        return round(sum(w.confidence for w in self.words) / len(self.words), 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ocr_line_id": self.ocr_line_id,
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
            "words": [w.to_dict() for w in self.words],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OcrLine:
        return cls(
            ocr_line_id=data["ocr_line_id"],
            text=data["text"],
            confidence=data["confidence"],
            bounding_box=BoundingBox.from_dict(data["bounding_box"]),
            words=tuple(OcrWord.from_dict(w) for w in data.get("words", [])),
            metadata=data.get("metadata", {}),
        )
