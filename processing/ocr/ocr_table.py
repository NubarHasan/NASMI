from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import generate_ocr_table_id, is_valid_ocr_table_id
from core.types import ConfidenceScore, Metadata, OcrTableId
from processing.ocr.bounding_box import BoundingBox
from processing.ocr.ocr_cell import OcrCell
from processing.ocr.ocr_row import OcrRow


@dataclass(frozen=True)
class OcrTable:
    table_id: OcrTableId
    page_number: int
    rows: tuple[OcrRow, ...]
    bounding_box: BoundingBox
    confidence: ConfidenceScore
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.table_id, str), "table_id must be a str")
        require(
            is_valid_ocr_table_id(self.table_id),
            "table_id must be a valid OcrTableId",
        )
        require(isinstance(self.page_number, int), "page_number must be an int")
        require(self.page_number >= 1, "page_number must be >= 1")
        require(isinstance(self.rows, tuple), "rows must be a tuple")
        require(len(self.rows) > 0, "rows must not be empty")
        require(
            all(isinstance(r, OcrRow) for r in self.rows),
            "every element of rows must be an OcrRow",
        )
        _row_indexes = [r.row_index for r in self.rows]
        require(
            _row_indexes == sorted(_row_indexes),
            "rows must be ordered by row_index (ascending)",
        )
        require(
            len(_row_indexes) == len(set(_row_indexes)),
            "row_index must be unique across rows",
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
        page_number: int,
        rows: list[OcrRow] | tuple[OcrRow, ...],
        bounding_box: BoundingBox,
        confidence: ConfidenceScore,
        metadata: Metadata | None = None,
    ) -> OcrTable:
        return cls(
            table_id=generate_ocr_table_id(),
            page_number=page_number,
            rows=tuple(rows),
            bounding_box=bounding_box,
            confidence=confidence,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        table_id: OcrTableId,
        page_number: int,
        rows: list[OcrRow] | tuple[OcrRow, ...],
        bounding_box: BoundingBox,
        confidence: ConfidenceScore,
        metadata: Metadata | None = None,
    ) -> OcrTable:
        return cls(
            table_id=table_id,
            page_number=page_number,
            rows=tuple(rows),
            bounding_box=bounding_box,
            confidence=confidence,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return max((r.column_count for r in self.rows), default=0)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        return round(
            sum(r.confidence for r in self.rows) / len(self.rows),
            4,
        )

    @property
    def is_confident(self) -> bool:
        return self.mean_confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def all_cells(self) -> tuple[OcrCell, ...]:
        return tuple(cell for row in self.rows for cell in row.cells)

    def row_at(self, row_index: int) -> OcrRow | None:
        for row in self.rows:
            if row.row_index == row_index:
                return row
        return None

    def cell_at(self, row_index: int, column_index: int) -> OcrCell | None:
        row = self.row_at(row_index)
        if row is None:
            return None
        return row.cell_at(column_index)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "page_number": self.page_number,
            "rows": [r.to_dict() for r in self.rows],
            "bounding_box": self.bounding_box.to_dict(),
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OcrTable:
        return cls(
            table_id=data["table_id"],
            page_number=data["page_number"],
            rows=tuple(OcrRow.from_dict(r) for r in data["rows"]),
            bounding_box=BoundingBox.from_dict(data["bounding_box"]),
            confidence=data["confidence"],
            metadata=data.get("metadata", {}),
        )
