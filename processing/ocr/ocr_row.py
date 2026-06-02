from __future__ import annotations

from dataclasses import dataclass, field

from core.guards import require
from core.identifiers import generate_ocr_row_id, is_valid_ocr_row_id
from core.types import ConfidenceScore, Metadata, OcrRowId
from processing.ocr.bounding_box import BoundingBox
from processing.ocr.ocr_cell import OcrCell


@dataclass(frozen=True)
class OcrRow:
    row_id: OcrRowId
    row_index: int
    cells: tuple[OcrCell, ...]
    bounding_box: BoundingBox
    confidence: ConfidenceScore
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.row_id, str), "row_id must be a str")
        require(is_valid_ocr_row_id(self.row_id), "row_id must be a valid OcrRowId")
        require(isinstance(self.row_index, int), "row_index must be an int")
        require(self.row_index >= 0, "row_index must be >= 0")
        require(isinstance(self.cells, tuple), "cells must be a tuple")
        require(len(self.cells) > 0, "cells must not be empty")
        require(
            all(isinstance(c, OcrCell) for c in self.cells),
            "every element of cells must be an OcrCell",
        )
        require(
            all(c.row_index == self.row_index for c in self.cells),
            "every cell.row_index must equal row_index",
        )
        _col_indexes = [c.column_index for c in self.cells]
        require(
            _col_indexes == sorted(_col_indexes),
            "cells must be ordered by column_index (ascending)",
        )
        require(
            len(_col_indexes) == len(set(_col_indexes)),
            "column_index must be unique across cells",
        )
        require(
            isinstance(self.bounding_box, BoundingBox),
            "bounding_box must be a BoundingBox",
        )
        require(
            isinstance(self.confidence, (int, float)),
            "confidence must be a number",
        )
        require(
            0.0 <= self.confidence <= 1.0,
            "confidence must be in [0.0, 1.0]",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        row_index: int,
        cells: list[OcrCell] | tuple[OcrCell, ...],
        bounding_box: BoundingBox,
        confidence: ConfidenceScore,
        metadata: Metadata | None = None,
    ) -> OcrRow:
        return cls(
            row_id=generate_ocr_row_id(),
            row_index=row_index,
            cells=tuple(cells),
            bounding_box=bounding_box,
            confidence=confidence,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        row_id: OcrRowId,
        row_index: int,
        cells: list[OcrCell] | tuple[OcrCell, ...],
        bounding_box: BoundingBox,
        confidence: ConfidenceScore,
        metadata: Metadata | None = None,
    ) -> OcrRow:
        return cls(
            row_id=row_id,
            row_index=row_index,
            cells=tuple(cells),
            bounding_box=bounding_box,
            confidence=confidence,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def column_count(self) -> int:
        return len(self.cells)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        return round(
            sum(c.confidence for c in self.cells) / len(self.cells),
            4,
        )

    @property
    def is_confident(self) -> bool:
        return self.mean_confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def any_low_confidence(self) -> bool:
        return any(c.confidence < 0.5 for c in self.cells)

    @property
    def reconstructed_text(self) -> str:
        return " | ".join(c.text or "" for c in self.cells)

    def cell_at(self, column_index: int) -> OcrCell | None:
        for cell in self.cells:
            if cell.column_index == column_index:
                return cell
        return None
