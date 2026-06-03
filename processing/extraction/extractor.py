from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.types import ExtractorId
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult


@runtime_checkable
class Extractor(Protocol):

    @property
    def extractor_id(self) -> ExtractorId: ...

    @property
    def supported_document_types(self) -> frozenset[str]: ...

    def can_handle(
        self,
        request: ExtractionRequest,
    ) -> bool: ...

    def extract(
        self,
        request: ExtractionRequest,
    ) -> ExtractionResult: ...
