from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_ocr_result_id,
    is_valid_ocr_result_id,
    is_valid_source_id,
)
from core.types import ConfidenceScore, Metadata, OcrResultId, SourceId
from processing.ocr.ocr_page import OcrPage


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
            "pages must be ordered by page_number (ascending)",
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
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def mean_confidence(self) -> ConfidenceScore:
        if not self.pages:
            return 0.0
        return round(sum(p.mean_confidence for p in self.pages) / len(self.pages), 4)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.full_text for p in self.pages)

    @property
    def total_block_count(self) -> int:
        return sum(p.block_count for p in self.pages)

    @property
    def total_table_count(self) -> int:
        return sum(p.table_count for p in self.pages)

    def page_at(self, page_number: int) -> OcrPage | None:
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ocr_result_id": self.ocr_result_id,
            "source_id": self.source_id,
            "pages": [p.to_dict() for p in self.pages],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OcrResult:
        return cls(
            ocr_result_id=data["ocr_result_id"],
            source_id=data["source_id"],
            pages=tuple(OcrPage.from_dict(p) for p in data["pages"]),
            metadata=data.get("metadata", {}),
        )
