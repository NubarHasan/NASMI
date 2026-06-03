from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from core.guards import require
from core.identifiers import generate_span_id, is_valid_span_id
from core.types import (
    ConfidenceScore,
    DocumentId,
    OcrBlockId,
    OcrCellId,
    OcrLineId,
    OcrTableId,
    OcrWordId,
    PageNumber,
    SourceId,
    SpanId,
)
from processing.ocr.bounding_box import BoundingBox

if TYPE_CHECKING:
    from processing.ocr.ocr_result import OcrResult

_MIN_CONFIDENCE: float = 0.0
_MAX_CONFIDENCE: float = 1.0
_MIN_PAGE_NUMBER: int = 1
_MIN_DIMENSION: float = 0.0


class ExtractableSpanType(StrEnum):
    WORD = "word"
    LINE = "line"
    BLOCK = "block"
    TABLE_CELL = "table_cell"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PageDimensions:
    page_number: PageNumber
    width_px: float
    height_px: float

    def __post_init__(self) -> None:
        require(
            isinstance(self.page_number, int) and self.page_number >= _MIN_PAGE_NUMBER,
            f"page_number must be a positive int, got [{self.page_number}]",
        )
        require(
            isinstance(self.width_px, (int, float)) and self.width_px > _MIN_DIMENSION,
            f"width_px must be positive, got [{self.width_px}]",
        )
        require(
            isinstance(self.height_px, (int, float))
            and self.height_px > _MIN_DIMENSION,
            f"height_px must be positive, got [{self.height_px}]",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width_px": self.width_px,
            "height_px": self.height_px,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PageDimensions:
        return cls(
            page_number=int(data["page_number"]),
            width_px=float(data["width_px"]),
            height_px=float(data["height_px"]),
        )

    @classmethod
    def from_ocr_page(cls, page: Any) -> PageDimensions:
        return cls(
            page_number=page.page_number,
            width_px=float(page.width),
            height_px=float(page.height),
        )


@dataclass(frozen=True)
class SpanSource:
    block_id: OcrBlockId | None = None
    line_id: OcrLineId | None = None
    word_ids: tuple[OcrWordId, ...] = field(default_factory=tuple)
    table_id: OcrTableId | None = None
    cell_id: OcrCellId | None = None
    row_index: int | None = None
    column_index: int | None = None

    def __post_init__(self) -> None:
        require(
            self.block_id is None or isinstance(self.block_id, str),
            "block_id must be a str or None",
        )
        require(
            self.line_id is None or isinstance(self.line_id, str),
            "line_id must be a str or None",
        )
        require(isinstance(self.word_ids, tuple), "word_ids must be a tuple")
        require(
            all(isinstance(w, str) and bool(w.strip()) for w in self.word_ids),
            "word_ids must contain non-empty strings",
        )
        require(
            self.table_id is None or isinstance(self.table_id, str),
            "table_id must be a str or None",
        )
        require(
            self.cell_id is None or isinstance(self.cell_id, str),
            "cell_id must be a str or None",
        )
        require(
            self.row_index is None
            or (isinstance(self.row_index, int) and self.row_index >= 0),
            f"row_index must be a non-negative int or None, got [{self.row_index}]",
        )
        require(
            self.column_index is None
            or (isinstance(self.column_index, int) and self.column_index >= 0),
            f"column_index must be a non-negative int or None, got [{self.column_index}]",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "line_id": self.line_id,
            "word_ids": list(self.word_ids),
            "table_id": self.table_id,
            "cell_id": self.cell_id,
            "row_index": self.row_index,
            "column_index": self.column_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpanSource:
        return cls(
            block_id=data.get("block_id"),
            line_id=data.get("line_id"),
            word_ids=tuple(data.get("word_ids") or []),
            table_id=data.get("table_id"),
            cell_id=data.get("cell_id"),
            row_index=data.get("row_index"),
            column_index=data.get("column_index"),
        )

    @classmethod
    def for_block(
        cls,
        block_id: OcrBlockId,
        line_id: OcrLineId,
        word_ids: tuple[OcrWordId, ...],
    ) -> SpanSource:
        return cls(block_id=block_id, line_id=line_id, word_ids=word_ids)

    @classmethod
    def for_line(
        cls,
        block_id: OcrBlockId,
        line_id: OcrLineId,
        word_ids: tuple[OcrWordId, ...],
    ) -> SpanSource:
        return cls(block_id=block_id, line_id=line_id, word_ids=word_ids)

    @classmethod
    def for_word(
        cls,
        block_id: OcrBlockId,
        line_id: OcrLineId,
        word_id: OcrWordId,
    ) -> SpanSource:
        return cls(block_id=block_id, line_id=line_id, word_ids=(word_id,))

    @classmethod
    def for_cell(
        cls,
        table_id: OcrTableId,
        cell_id: OcrCellId,
        row_index: int,
        column_index: int,
    ) -> SpanSource:
        return cls(
            table_id=table_id,
            cell_id=cell_id,
            row_index=row_index,
            column_index=column_index,
        )


@dataclass(frozen=True)
class ExtractableSpan:
    span_id: SpanId
    span_type: ExtractableSpanType
    text: str
    page_number: PageNumber
    bounding_box: BoundingBox
    confidence: ConfidenceScore
    source: SpanSource
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(is_valid_span_id(self.span_id), f"Invalid SpanId: [{self.span_id}]")
        require(
            isinstance(self.span_type, ExtractableSpanType),
            f"span_type must be ExtractableSpanType, got [{type(self.span_type)}]",
        )
        require(isinstance(self.text, str), "text must be a string")
        require(bool(self.text.strip()), "text must not be empty")
        require(
            isinstance(self.page_number, int) and self.page_number >= _MIN_PAGE_NUMBER,
            f"page_number must be a positive int, got [{self.page_number}]",
        )
        require(
            isinstance(self.bounding_box, BoundingBox),
            "bounding_box must be a BoundingBox instance",
        )
        require(
            isinstance(self.confidence, (int, float))
            and _MIN_CONFIDENCE <= self.confidence <= _MAX_CONFIDENCE,
            f"confidence must be in [0.0, 1.0], got [{self.confidence}]",
        )
        require(isinstance(self.source, SpanSource), "source must be a SpanSource")
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.9

    def with_metadata(self, key: str, value: Any) -> ExtractableSpan:
        return ExtractableSpan(
            span_id=self.span_id,
            span_type=self.span_type,
            text=self.text,
            page_number=self.page_number,
            bounding_box=self.bounding_box,
            confidence=self.confidence,
            source=self.source,
            metadata={**self.metadata, key: value},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "span_type": str(self.span_type),
            "text": self.text,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box.to_dict(),
            "confidence": self.confidence,
            "source": self.source.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractableSpan:
        return cls(
            span_id=SpanId(data["span_id"]),
            span_type=ExtractableSpanType(data["span_type"]),
            text=data["text"],
            page_number=int(data["page_number"]),
            bounding_box=BoundingBox.from_dict(data["bounding_box"]),
            confidence=float(data["confidence"]),
            source=SpanSource.from_dict(data["source"]),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def create(
        cls,
        span_type: ExtractableSpanType,
        text: str,
        page_number: PageNumber,
        bounding_box: BoundingBox,
        confidence: ConfidenceScore,
        source: SpanSource,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractableSpan:
        return cls(
            span_id=generate_span_id(),
            span_type=span_type,
            text=text,
            page_number=page_number,
            bounding_box=bounding_box,
            confidence=confidence,
            source=source,
            metadata=dict(metadata) if metadata is not None else {},
        )


def _word_based_confidence(line: Any) -> ConfidenceScore:
    if not line.has_words:
        return float(line.confidence)
    return float(round(sum(w.confidence for w in line.words) / len(line.words), 4))


def _block_confidence_from_words(block: Any) -> ConfidenceScore:
    words = [w for line in block.lines for w in line.words]
    if not words:
        return float(block.confidence)
    return float(round(sum(w.confidence for w in words) / len(words), 4))


def _build_block_spans(page: Any) -> list[ExtractableSpan]:
    spans: list[ExtractableSpan] = []

    for block in page.blocks:
        if not block.lines:
            continue

        all_words = [w for line in block.lines for w in line.words]
        all_word_ids = tuple(w.ocr_word_id for w in all_words)
        first_line = block.lines[0]
        block_text = block.reconstructed_text.strip()

        if not block_text:
            continue

        spans.append(
            ExtractableSpan.create(
                span_type=ExtractableSpanType.BLOCK,
                text=block_text,
                page_number=page.page_number,
                bounding_box=block.bounding_box,
                confidence=_block_confidence_from_words(block),
                source=SpanSource.for_block(
                    block_id=block.ocr_block_id,
                    line_id=first_line.ocr_line_id,
                    word_ids=all_word_ids,
                ),
            )
        )

        for line in block.lines:
            line_text = line.reconstructed_text.strip()
            if not line_text:
                continue

            line_word_ids = tuple(w.ocr_word_id for w in line.words)

            spans.append(
                ExtractableSpan.create(
                    span_type=ExtractableSpanType.LINE,
                    text=line_text,
                    page_number=page.page_number,
                    bounding_box=line.bounding_box,
                    confidence=_word_based_confidence(line),
                    source=SpanSource.for_line(
                        block_id=block.ocr_block_id,
                        line_id=line.ocr_line_id,
                        word_ids=line_word_ids,
                    ),
                )
            )

            for word in line.words:
                word_text = word.text.strip()
                if not word_text:
                    continue

                spans.append(
                    ExtractableSpan.create(
                        span_type=ExtractableSpanType.WORD,
                        text=word_text,
                        page_number=page.page_number,
                        bounding_box=word.bounding_box,
                        confidence=word.confidence,
                        source=SpanSource.for_word(
                            block_id=block.ocr_block_id,
                            line_id=line.ocr_line_id,
                            word_id=word.ocr_word_id,
                        ),
                    )
                )

    return spans


def _build_table_spans(page: Any) -> list[ExtractableSpan]:
    spans: list[ExtractableSpan] = []

    for table in page.tables:
        for row in table.rows:
            for cell in row.cells:
                if not cell.has_text:
                    continue

                spans.append(
                    ExtractableSpan.create(
                        span_type=ExtractableSpanType.TABLE_CELL,
                        text=cell.text_stripped,
                        page_number=page.page_number,
                        bounding_box=cell.bounding_box,
                        confidence=cell.confidence,
                        source=SpanSource.for_cell(
                            table_id=table.table_id,
                            cell_id=cell.cell_id,
                            row_index=cell.row_index,
                            column_index=cell.column_index,
                        ),
                    )
                )

    return spans


@dataclass(frozen=True)
class ExtractableSpatialData:
    source_id: SourceId
    document_id: DocumentId
    spans: tuple[ExtractableSpan, ...]
    page_count: int
    mean_confidence: ConfidenceScore
    reconstructed_text: str
    page_dimensions: tuple[PageDimensions, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        require(
            isinstance(self.source_id, str) and bool(self.source_id.strip()),
            "source_id must be a non-empty string",
        )
        require(
            isinstance(self.document_id, str) and bool(self.document_id.strip()),
            "document_id must be a non-empty string",
        )
        require(isinstance(self.spans, tuple), "spans must be a tuple")
        require(
            all(isinstance(s, ExtractableSpan) for s in self.spans),
            "all spans must be ExtractableSpan instances",
        )
        require(
            isinstance(self.page_count, int) and self.page_count >= 1,
            f"page_count must be >= 1, got [{self.page_count}]",
        )
        require(
            isinstance(self.mean_confidence, (int, float))
            and _MIN_CONFIDENCE <= self.mean_confidence <= _MAX_CONFIDENCE,
            f"mean_confidence must be in [0.0, 1.0], got [{self.mean_confidence}]",
        )
        require(
            isinstance(self.reconstructed_text, str),
            "reconstructed_text must be a string",
        )
        require(
            isinstance(self.page_dimensions, tuple),
            "page_dimensions must be a tuple",
        )
        require(
            all(isinstance(p, PageDimensions) for p in self.page_dimensions),
            "all page_dimensions must be PageDimensions instances",
        )

    def find_by_text(
        self,
        query: str,
        *,
        case_sensitive: bool = False,
    ) -> tuple[ExtractableSpan, ...]:
        if not case_sensitive:
            query = query.lower()
            return tuple(s for s in self.spans if query in s.text.lower())
        return tuple(s for s in self.spans if query in s.text)

    def spans_for_page(self, page_number: int) -> tuple[ExtractableSpan, ...]:
        require(
            1 <= page_number <= self.page_count,
            f"page_number [{page_number}] out of range [1..{self.page_count}]",
        )
        return tuple(s for s in self.spans if s.page_number == page_number)

    def spans_by_type(
        self, span_type: ExtractableSpanType
    ) -> tuple[ExtractableSpan, ...]:
        return tuple(s for s in self.spans if s.span_type == span_type)

    def low_confidence_spans(
        self, threshold: float = 0.5
    ) -> tuple[ExtractableSpan, ...]:
        require(
            _MIN_CONFIDENCE <= threshold <= _MAX_CONFIDENCE,
            f"threshold must be in [0.0, 1.0], got [{threshold}]",
        )
        return tuple(s for s in self.spans if s.confidence < threshold)

    def high_confidence_spans(
        self, threshold: float = 0.9
    ) -> tuple[ExtractableSpan, ...]:
        require(
            _MIN_CONFIDENCE <= threshold <= _MAX_CONFIDENCE,
            f"threshold must be in [0.0, 1.0], got [{threshold}]",
        )
        return tuple(s for s in self.spans if s.confidence >= threshold)

    def spans_in_block(self, block_id: OcrBlockId) -> tuple[ExtractableSpan, ...]:
        return tuple(s for s in self.spans if s.source.block_id == block_id)

    def spans_in_table(self, table_id: OcrTableId) -> tuple[ExtractableSpan, ...]:
        return tuple(s for s in self.spans if s.source.table_id == table_id)

    def dimensions_for_page(self, page_number: int) -> PageDimensions | None:
        for pd in self.page_dimensions:
            if pd.page_number == page_number:
                return pd
        return None

    @property
    def span_count(self) -> int:
        return len(self.spans)

    @property
    def is_empty(self) -> bool:
        return len(self.spans) == 0

    @property
    def is_low_quality(self) -> bool:
        return self.mean_confidence < 0.5

    @property
    def has_dimensions(self) -> bool:
        return len(self.page_dimensions) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "document_id": self.document_id,
            "spans": [s.to_dict() for s in self.spans],
            "page_count": self.page_count,
            "mean_confidence": self.mean_confidence,
            "reconstructed_text": self.reconstructed_text,
            "page_dimensions": [p.to_dict() for p in self.page_dimensions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractableSpatialData:
        return cls(
            source_id=SourceId(data["source_id"]),
            document_id=DocumentId(data["document_id"]),
            spans=tuple(ExtractableSpan.from_dict(s) for s in data.get("spans", [])),
            page_count=int(data["page_count"]),
            mean_confidence=float(data["mean_confidence"]),
            reconstructed_text=data.get("reconstructed_text", ""),
            page_dimensions=tuple(
                PageDimensions.from_dict(p) for p in data.get("page_dimensions", [])
            ),
        )

    @classmethod
    def from_ocr_result(
        cls,
        result: OcrResult,
        source_id: SourceId,
        document_id: DocumentId,
    ) -> ExtractableSpatialData:
        spans: list[ExtractableSpan] = []
        dimensions: list[PageDimensions] = []

        for page in result.pages:
            spans.extend(_build_block_spans(page))
            spans.extend(_build_table_spans(page))
            dimensions.append(PageDimensions.from_ocr_page(page))

        return cls(
            source_id=source_id,
            document_id=document_id,
            spans=tuple(spans),
            page_count=result.page_count,
            mean_confidence=result.mean_confidence,
            reconstructed_text=result.full_text,
            page_dimensions=tuple(dimensions),
        )
