from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import generate_ocr_page_id, is_valid_ocr_page_id
from core.types import ConfidenceScore, Metadata, OcrPageId
from processing.ocr.ocr_block import OcrBlock
from processing.ocr.ocr_table import OcrTable

_MIN_DIMENSION: float = 0.0


@dataclass(frozen=True)
class OcrPage:
    ocr_page_id: OcrPageId
    page_number: int
    width: float
    height: float
    blocks: tuple[OcrBlock, ...]
    tables: tuple[OcrTable, ...]
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.ocr_page_id, str), "ocr_page_id must be a str")
        require(
            is_valid_ocr_page_id(self.ocr_page_id),
            "ocr_page_id must be a valid OcrPageId",
        )
        require(isinstance(self.page_number, int), "page_number must be an int")
        require(self.page_number > 0, "page_number must be positive")
        require(isinstance(self.width, (int, float)), "width must be a number")
        require(self.width > _MIN_DIMENSION, "width must be positive")
        require(isinstance(self.height, (int, float)), "height must be a number")
        require(self.height > _MIN_DIMENSION, "height must be positive")
        require(isinstance(self.blocks, tuple), "blocks must be a tuple")
        require(
            all(isinstance(b, OcrBlock) for b in self.blocks),
            "every element of blocks must be an OcrBlock",
        )
        require(isinstance(self.tables, tuple), "tables must be a tuple")
        require(
            all(isinstance(t, OcrTable) for t in self.tables),
            "every element of tables must be an OcrTable",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        page_number: int,
        width: float,
        height: float,
        blocks: list[OcrBlock] | tuple[OcrBlock, ...] | None = None,
        tables: list[OcrTable] | tuple[OcrTable, ...] | None = None,
        metadata: Metadata | None = None,
    ) -> OcrPage:
        return cls(
            ocr_page_id=generate_ocr_page_id(),
            page_number=page_number,
            width=width,
            height=height,
            blocks=tuple(blocks) if blocks is not None else (),
            tables=tuple(tables) if tables is not None else (),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        ocr_page_id: OcrPageId,
        page_number: int,
        width: float,
        height: float,
        blocks: list[OcrBlock] | tuple[OcrBlock, ...],
        tables: list[OcrTable] | tuple[OcrTable, ...],
        metadata: Metadata | None = None,
    ) -> OcrPage:
        return cls(
            ocr_page_id=ocr_page_id,
            page_number=page_number,
            width=width,
            height=height,
            blocks=tuple(blocks),
            tables=tuple(tables),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def has_blocks(self) -> bool:
        return len(self.blocks) > 0

    @property
    def has_tables(self) -> bool:
        return len(self.tables) > 0

    @property
    def mean_confidence(self) -> ConfidenceScore:
        total = sum(b.confidence for b in self.blocks) + sum(
            t.confidence for t in self.tables
        )
        count = len(self.blocks) + len(self.tables)
        if count == 0:
            return 0.0
        return round(total / count, 4)

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ocr_page_id": self.ocr_page_id,
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "blocks": [b.to_dict() for b in self.blocks],
            "tables": [t.to_dict() for t in self.tables],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OcrPage:
        return cls(
            ocr_page_id=data["ocr_page_id"],
            page_number=data["page_number"],
            width=data["width"],
            height=data["height"],
            blocks=tuple(OcrBlock.from_dict(b) for b in data.get("blocks", [])),
            tables=tuple(OcrTable.from_dict(t) for t in data.get("tables", [])),
            metadata=data.get("metadata", {}),
        )
