from __future__ import annotations

from dataclasses import dataclass, field

from core.guards import require
from core.identifiers import generate_ocr_cell_id, is_valid_ocr_cell_id
from core.types import ConfidenceScore, Metadata, OcrCellId
from processing.ocr.bounding_box import BoundingBox


@dataclass(frozen=True)
class OcrCell:
    cell_id: OcrCellId
    row_index: int
    column_index: int
    text: str | None
    confidence: ConfidenceScore
    bounding_box: BoundingBox
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.cell_id, str), "cell_id must be a str")
        require(is_valid_ocr_cell_id(self.cell_id), "cell_id must be a valid OcrCellId")
        require(isinstance(self.row_index, int), "row_index must be an int")
        require(self.row_index >= 0, "row_index must be >= 0")
        require(isinstance(self.column_index, int), "column_index must be an int")
        require(self.column_index >= 0, "column_index must be >= 0")
        require(
            self.text is None or isinstance(self.text, str),
            "text must be a str or None",
        )
        require(
            isinstance(self.confidence, (int, float)), "confidence must be a number"
        )
        require(0.0 <= self.confidence <= 1.0, "confidence must be in [0.0, 1.0]")
        require(
            isinstance(self.bounding_box, BoundingBox),
            "bounding_box must be a BoundingBox",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        row_index: int,
        column_index: int,
        text: str | None,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        metadata: Metadata | None = None,
    ) -> OcrCell:
        return cls(
            cell_id=generate_ocr_cell_id(),
            row_index=row_index,
            column_index=column_index,
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        cell_id: OcrCellId,
        row_index: int,
        column_index: int,
        text: str | None,
        confidence: ConfidenceScore,
        bounding_box: BoundingBox,
        metadata: Metadata | None = None,
    ) -> OcrCell:
        return cls(
            cell_id=cell_id,
            row_index=row_index,
            column_index=column_index,
            text=text,
            confidence=confidence,
            bounding_box=bounding_box,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def text_stripped(self) -> str | None:
        if self.text is None:
            return None
        stripped = self.text.strip()
        return stripped if stripped else None

    @property
    def has_text(self) -> bool:
        return self.text_stripped is not None

    @property
    def is_empty(self) -> bool:
        return self.text_stripped is None

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def coordinate(self) -> tuple[int, int]:
        return (self.row_index, self.column_index)

    @property
    def char_count(self) -> int:
        return len(self.text) if self.text is not None else 0

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text is not None else 0
