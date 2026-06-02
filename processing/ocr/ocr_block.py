from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from core.guards import require
from core.identifiers import generate_ocr_block_id, is_valid_ocr_block_id
from core.types import ConfidenceScore, Metadata, OcrBlockId
from processing.ocr.bounding_box import BoundingBox
from processing.ocr.ocr_line import OcrLine

_MIN_CONFIDENCE: ConfidenceScore = 0.0
_MAX_CONFIDENCE: ConfidenceScore = 1.0


class OcrBlockType(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    HEADER = "header"
    FOOTER = "footer"
    CAPTION = "caption"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OcrBlock:
    ocr_block_id: OcrBlockId
    text: str
    confidence: ConfidenceScore
    bounding_box: BoundingBox
    block_type: OcrBlockType
    lines: tuple[OcrLine, ...]
    region_image_path: Path | None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.ocr_block_id, str), "ocr_block_id must be a str")
        require(
            is_valid_ocr_block_id(self.ocr_block_id),
            "ocr_block_id must be a valid OcrBlockId",
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
        require(
            isinstance(self.block_type, OcrBlockType),
            "block_type must be an OcrBlockType",
        )
        require(isinstance(self.lines, tuple), "lines must be a tuple")
        require(
            all(isinstance(ln, OcrLine) for ln in self.lines),
            "every element of lines must be an OcrLine",
        )
        require(
            self.region_image_path is None or isinstance(self.region_image_path, Path),
            "region_image_path must be a Path or None",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        text: str,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        block_type: OcrBlockType = OcrBlockType.PARAGRAPH,
        lines: list[OcrLine] | tuple[OcrLine, ...] | None = None,
        region_image_path: Path | None = None,
        metadata: Metadata | None = None,
    ) -> OcrBlock:
        return cls(
            ocr_block_id=generate_ocr_block_id(),
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            block_type=block_type,
            lines=tuple(lines) if lines is not None else (),
            region_image_path=region_image_path,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        ocr_block_id: OcrBlockId,
        text: str,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        block_type: OcrBlockType,
        lines: list[OcrLine] | tuple[OcrLine, ...],
        region_image_path: Path | None = None,
        metadata: Metadata | None = None,
    ) -> OcrBlock:
        return cls(
            ocr_block_id=ocr_block_id,
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            block_type=block_type,
            lines=tuple(lines),
            region_image_path=region_image_path,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def has_lines(self) -> bool:
        return len(self.lines) > 0

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def word_count(self) -> int:
        return sum(ln.word_count for ln in self.lines)

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
    def has_evidence(self) -> bool:
        return self.region_image_path is not None

    @property
    def reconstructed_text(self) -> str:
        if not self.has_lines:
            return self.text
        return "\n".join(ln.text for ln in self.lines)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        if not self.has_lines:
            return self.confidence
        return round(sum(ln.mean_confidence for ln in self.lines) / len(self.lines), 4)
