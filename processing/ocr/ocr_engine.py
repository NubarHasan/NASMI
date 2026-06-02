from __future__ import annotations

from typing import Protocol, runtime_checkable

from processing.ocr.ocr_request import OcrRequest
from processing.ocr.ocr_result import OcrResult


@runtime_checkable
class OcrEngine(Protocol):

    @property
    def engine_name(self) -> str: ...

    @property
    def engine_version(self) -> str | None: ...

    def process(
        self,
        request: OcrRequest,
    ) -> OcrResult: ...
