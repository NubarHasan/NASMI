from __future__ import annotations

from typing import Protocol

from extraction.extraction_request import ExtractionRequest
from extraction.extraction_result import ExtractionResult


class Extractor(Protocol):

    def extract(
        self,
        request: ExtractionRequest,
    ) -> ExtractionResult: ...
