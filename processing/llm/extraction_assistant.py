from __future__ import annotations

from typing import Any

from processing.llm.llm_port import LLMPort
from processing.llm.llm_response import LLMResponse


class ExtractionAssistant:

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def suggest_fields(self, raw_text: str) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Suggest extractable fields from the following text:\n\n{raw_text}",
            context={"task": "suggest_fields"},
        )

    def suggest_ocr_correction(self, raw_text: str) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Suggest OCR corrections for the following text:\n\n{raw_text}",
            context={"task": "suggest_ocr_correction"},
        )

    def suggest_missing_values(
        self,
        raw_text: str,
        known_fields: dict[str, Any],
    ) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Suggest missing values based on context:\n\n{raw_text}",
            context={"task": "suggest_missing_values", "known_fields": known_fields},
        )

    def suggest_document_class(self, raw_text: str) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Suggest the document classification for:\n\n{raw_text}",
            context={"task": "suggest_document_class"},
        )
