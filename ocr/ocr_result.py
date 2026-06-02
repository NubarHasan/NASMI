from __future__ import annotations

from dataclasses import dataclass, field

from core.guards import require
from core.identifiers import (
    generate_ocr_result_id,
    is_valid_ocr_result_id,
    is_valid_source_id,
)
from core.types import ConfidenceScore, Metadata, OcrResultId, SourceId
from ocr.ocr_page import OcrPage


@dataclass(frozen=True)
class OcrResult:
    ocr_result_id: OcrResultId
    source_id: SourceId
    pages: tuple[OcrPage, ...]
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.ocr_result_id, str), "ocr_result_id must be a str")
        require(
            is_valid_ocr_result_id(self.ocr_result_id),
            "ocr_result_id must be a valid OcrResultId",
        )
        require(isinstance(self.source_id, str), "source_id must be a str")
        require(
            is_valid_source_id(self.source_id), "source_id must be a valid SourceId"
        )
        require(isinstance(self.pages, tuple), "pages must be a tuple")
        require(
            all(isinstance(p, OcrPage) for p in self.pages),
            "every element of pages must be an OcrPage",
        )
        require(len(self.pages) > 0, "pages must not be empty")
        _page_numbers = [p.page_number for p in self.pages]
        require(
            _page_numbers == sorted(_page_numbers),
            "pages must be ordered by page_number",
        )
        require(
            len(_page_numbers) == len(set(_page_numbers)),
            "page_number must be unique across pages",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def create(
        cls,
        source_id: SourceId,
        pages: list[OcrPage] | tuple[OcrPage, ...],
        metadata: Metadata | None = None,
    ) -> OcrResult:
        return cls(
            ocr_result_id=generate_ocr_result_id(),
            source_id=source_id,
            pages=tuple(pages),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        ocr_result_id: OcrResultId,
        source_id: SourceId,
        pages: list[OcrPage] | tuple[OcrPage, ...],
        metadata: Metadata | None = None,
    ) -> OcrResult:
        return cls(
            ocr_result_id=ocr_result_id,
            source_id=source_id,
            pages=tuple(pages),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def has_tables(self) -> bool:
        return any(p.has_tables for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def page_numbers(self) -> tuple[int, ...]:
        return tuple(p.page_number for p in self.pages)

    @property
    def block_count(self) -> int:
        return sum(p.block_count for p in self.pages)

    @property
    def table_count(self) -> int:
        return sum(p.table_count for p in self.pages)

    @property
    def table_cell_count(self) -> int:
        return sum(p.table_cell_count for p in self.pages)

    @property
    def line_count(self) -> int:
        return sum(p.line_count for p in self.pages)

    @property
    def word_count(self) -> int:
        return sum(p.word_count for p in self.pages)

    @property
    def char_count(self) -> int:
        return len(self.reconstructed_text)

    @property
    def reconstructed_text(self) -> str:
        return "\n\n".join(p.reconstructed_text for p in self.pages)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        return round(
            sum(p.mean_confidence for p in self.pages) / len(self.pages),
            4,
        )

    @property
    def is_confident(self) -> bool:
        return self.mean_confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        return self.mean_confidence < 0.5
