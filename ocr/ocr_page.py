from __future__ import annotations

from dataclasses import dataclass, field

from core.guards import require
from core.identifiers import generate_ocr_page_id, is_valid_ocr_page_id
from core.types import ConfidenceScore, Metadata, OcrPageId
from ocr.ocr_block import OcrBlock
from ocr.ocr_table import OcrTable

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
        require(
            len(self.blocks) > 0 or len(self.tables) > 0,
            "page must contain at least one block or table",
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
    def has_blocks(self) -> bool:
        return len(self.blocks) > 0

    @property
    def has_tables(self) -> bool:
        return len(self.tables) > 0

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def table_cell_count(self) -> int:
        return sum(t.cell_count for t in self.tables)

    @property
    def line_count(self) -> int:
        return sum(b.line_count for b in self.blocks)

    @property
    def word_count(self) -> int:
        return sum(b.word_count for b in self.blocks)

    @property
    def char_count(self) -> int:
        return len(self.reconstructed_text)

    @property
    def reconstructed_text(self) -> str:
        parts: list[str] = []
        for block in self.blocks:
            parts.append(block.reconstructed_text)
        for table in self.tables:
            parts.append(table.reconstructed_text)
        return "\n\n".join(parts)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        sources = [*self.blocks, *self.tables]
        return round(
            sum(s.mean_confidence for s in sources) / len(sources),
            4,
        )

    @property
    def is_confident(self) -> bool:
        return self.mean_confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        return self.mean_confidence < 0.5
