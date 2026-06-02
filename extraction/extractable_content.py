from __future__ import annotations

from dataclasses import dataclass, field

from core.guards import require
from core.types import ConfidenceScore, LanguageCode, Metadata, PageCount
from extraction.spatial_data import ExtractableSpatialData


@dataclass(frozen=True)
class ExtractableContent:
    raw_text: str
    language: LanguageCode
    page_count: PageCount
    ocr_confidence: ConfidenceScore
    spatial_data: ExtractableSpatialData | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.raw_text, str),           "raw_text must be a string")
        require(bool(self.raw_text.strip()),               "raw_text must not be empty")
        require(isinstance(self.language, str),           "language must be a str (LanguageCode)")
        require(bool(self.language.strip()),               "language must not be empty")
        require(isinstance(self.page_count, int),         "page_count must be an int (PageCount)")
        require(self.page_count >= 1,                     "page_count must be >= 1")
        require(isinstance(self.ocr_confidence, (int, float)),
                                                          "ocr_confidence must be a number (ConfidenceScore)")
        require(0.0 <= self.ocr_confidence <= 1.0,        "ocr_confidence must be in [0.0, 1.0]")
        require(
            self.spatial_data is None
            or isinstance(self.spatial_data, ExtractableSpatialData),
            "spatial_data must be ExtractableSpatialData or None",
        )
        require(isinstance(self.metadata, dict),          "metadata must be a dict (Metadata)")

    @classmethod
    def create(
        cls,
        raw_text: str,
        language: LanguageCode,
        page_count: PageCount,
        ocr_confidence: ConfidenceScore,
        spatial_data: ExtractableSpatialData | None = None,
        metadata: Metadata | None = None,
    ) -> ExtractableContent:
        return cls(
            raw_text=raw_text,
            language=language,
            page_count=page_count,
            ocr_confidence=ocr_confidence,
            spatial_data=spatial_data,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def has_spatial_data(self) -> bool:
        return self.spatial_data is not None

    @property
    def is_low_quality(self) -> bool:
        return self.ocr_confidence < 0.5