from __future__ import annotations

import logging
import re

from core.guards import require
from core.types import DocumentId, ExtractorId, SourceId
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.extraction.extractor_registry import ExtractorRegistry

_log = logging.getLogger(__name__)

_UNKNOWN_EXTRACTOR = ExtractorId("unknown")
_UNKNOWN_TYPES = {"", "unknown", "other", "undefined", "none", "null"}

_DOC_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "passport",
        re.compile(
            r"reisepass|passport|p<[a-z]{3}|[A-Z0-9<]{30,44}",
            re.IGNORECASE,
        ),
    ),
    (
        "id_card",
        re.compile(
            r"personalausweis|identity\s+card|idcard|ID<[A-Z]{3}",
            re.IGNORECASE,
        ),
    ),
    (
        "residence_permit",
        re.compile(
            r"aufenthaltstitel|niederlassungserlaubnis|residence\s+permit",
            re.IGNORECASE,
        ),
    ),
    (
        "employment_contract",
        re.compile(
            r"arbeitsvertrag|employment\s+contract|arbeitnehmer.*arbeitgeber",
            re.IGNORECASE,
        ),
    ),
    (
        "payslip",
        re.compile(
            r"lohnabrechnung|gehaltsabrechnung|entgeltabrechnung|payslip|pay\s+slip",
            re.IGNORECASE,
        ),
    ),
    (
        "bank_statement",
        re.compile(
            r"kontoauszug|bank\s*statement|iban\s*:?\s*[A-Z]{2}\d{2}",
            re.IGNORECASE,
        ),
    ),
    (
        "invoice",
        re.compile(
            r"rechnung|invoice|rechnungsnummer|invoice\s+no",
            re.IGNORECASE,
        ),
    ),
]


def _is_unknown_document_type(value: str | None) -> bool:
    return value is None or value.strip().lower() in _UNKNOWN_TYPES


def _detect_document_type(text: str) -> str | None:
    if not text or not text.strip():
        return None
    for doc_type, pattern in _DOC_TYPE_PATTERNS:
        if pattern.search(text):
            _log.info("auto-detected document_type=%r", doc_type)
            return doc_type
    return None


class ExtractionService:

    def __init__(self, registry: ExtractorRegistry) -> None:
        require(
            isinstance(registry, ExtractorRegistry),
            "registry must be an ExtractorRegistry",
        )
        self._registry = registry

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        require(
            isinstance(request, ExtractionRequest),
            "request must be an ExtractionRequest",
        )

        document_id: DocumentId = request.content.document_id
        source_id: SourceId = request.content.source_id
        document_type: str | None = request.content.document_type

        if _is_unknown_document_type(document_type):
            detected = _detect_document_type(request.content.normalized_text)
            if detected is None:
                _log.warning(
                    "extraction: could not detect document_type — source_id=%r",
                    source_id,
                )
                return ExtractionResult.failure(
                    document_id=document_id,
                    source_id=source_id,
                    extractor_id=_UNKNOWN_EXTRACTOR,
                    metadata={"reason": "document_type could not be detected"},
                )

            document_type = detected
            request = ExtractionRequest.create(
                entity_id=request.entity_id,
                content=request.content.with_document_type(document_type),
                requested_fact_types=request.requested_fact_types,
            )

        extractor = self._registry.resolve(document_type)

        if extractor is None:
            detected = _detect_document_type(request.content.normalized_text)
            if detected is not None and detected != document_type:
                document_type = detected
                request = ExtractionRequest.create(
                    entity_id=request.entity_id,
                    content=request.content.with_document_type(document_type),
                    requested_fact_types=request.requested_fact_types,
                )
                extractor = self._registry.resolve(document_type)

        if extractor is None:
            _log.warning(
                "no extractor registered for document_type %r",
                document_type,
            )
            return ExtractionResult.failure(
                document_id=document_id,
                source_id=source_id,
                extractor_id=_UNKNOWN_EXTRACTOR,
                metadata={
                    "reason": f"no extractor for document_type {document_type!r}"
                },
            )

        if not extractor.can_handle(request):
            _log.warning(
                "extractor %r refused request for document_type %r",
                extractor.extractor_id,
                document_type,
            )
            return ExtractionResult.failure(
                document_id=document_id,
                source_id=source_id,
                extractor_id=extractor.extractor_id,
                metadata={
                    "reason": (
                        f"extractor {extractor.extractor_id!r} "
                        f"refused document_type {document_type!r}"
                    )
                },
            )

        _log.debug(
            "dispatching document_type %r to extractor %r",
            document_type,
            extractor.extractor_id,
        )
        return extractor.extract(request)
