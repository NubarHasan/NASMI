from __future__ import annotations

import logging
import re

from core.guards import require
from core.types import DocumentId, ExtractorId, SourceId
from processing.extraction.candidate_fact import CandidateFact
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.extraction.extractor_registry import ExtractorRegistry
from processing.extraction.extractors.universal_document_extractor import (
    UniversalDocumentExtractor,
)
from processing.extraction.quality_gate import filter_candidate_facts
from processing.llm.extraction_structurer import LLMExtractionStructurer
from processing.llm.llm_factory import make_extraction_llm

_log = logging.getLogger(__name__)

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
            r"arbeitsvertrag|employment\s+contract|internship\s+contract|arbeitnehmer.*arbeitgeber",
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


def _needs_llm_cleanup(
    document_type: str,
    text: str,
    candidate_count: int,
    quality_count: int,
) -> bool:
    normalized_type = document_type.strip().lower()
    lowered = text.lower()

    if normalized_type == "passport":
        return True

    if "passport" in lowered or "reisepass" in lowered:
        return True

    if candidate_count < 6:
        return True

    return quality_count < 4


class ExtractionService:
    def __init__(self, registry: ExtractorRegistry) -> None:
        require(
            isinstance(registry, ExtractorRegistry),
            "registry must be an ExtractorRegistry",
        )
        self._registry = registry
        self._universal = UniversalDocumentExtractor()
        self._llm_structurer: LLMExtractionStructurer | None = None

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        require(
            isinstance(request, ExtractionRequest),
            "request must be an ExtractionRequest",
        )

        document_id: DocumentId = request.content.document_id
        source_id: SourceId = request.content.source_id
        document_type: str | None = request.content.document_type
        text = request.content.normalized_text or request.content.raw_text or ""

        detected = _detect_document_type(text)

        if _is_unknown_document_type(document_type):
            document_type = detected or "universal"
            request = ExtractionRequest.create(
                entity_id=request.entity_id,
                content=request.content.with_document_type(document_type),
                requested_fact_types=request.requested_fact_types,
            )

        resolved_document_type = document_type or "universal"
        extractor = self._registry.resolve(resolved_document_type)

        if (
            extractor is None
            and detected is not None
            and detected != resolved_document_type
        ):
            resolved_document_type = detected
            request = ExtractionRequest.create(
                entity_id=request.entity_id,
                content=request.content.with_document_type(resolved_document_type),
                requested_fact_types=request.requested_fact_types,
            )
            extractor = self._registry.resolve(resolved_document_type)

        if extractor is None:
            _log.info(
                "no registered extractor for document_type=%r — using universal extractor",
                resolved_document_type,
            )
            raw_result = self._universal.extract(request)
            return self._structure_or_defer_llm_if_needed(
                text=text,
                raw_result=raw_result,
                document_type=resolved_document_type,
                strategy="universal_only_quality_gate",
            )

        if not extractor.can_handle(request):
            _log.info(
                "extractor %r refused document_type=%r — using universal extractor",
                extractor.extractor_id,
                resolved_document_type,
            )
            raw_result = self._universal.extract(request)
            return self._structure_or_defer_llm_if_needed(
                text=text,
                raw_result=raw_result,
                document_type=resolved_document_type,
                strategy="universal_fallback_quality_gate",
            )

        primary_result = extractor.extract(request)

        if not primary_result.succeeded:
            _log.info(
                "primary extractor failed for document_type=%r — using universal extractor",
                resolved_document_type,
            )
            raw_result = self._universal.extract(request)
            return self._structure_or_defer_llm_if_needed(
                text=text,
                raw_result=raw_result,
                document_type=resolved_document_type,
                strategy="universal_after_primary_failure_quality_gate",
            )

        universal_result = self._universal.extract(request)

        merged_facts = _merge_candidate_facts(
            list(primary_result.candidate_facts),
            list(universal_result.candidate_facts),
        )

        raw_result = ExtractionResult.success(
            document_id=document_id,
            source_id=source_id,
            extractor_id=ExtractorId(f"{primary_result.extractor_id}+universal"),
            candidate_facts=tuple(merged_facts),
            metadata={
                "primary_extractor": str(primary_result.extractor_id),
                "universal_extractor": str(universal_result.extractor_id),
                "primary_candidate_count": primary_result.candidate_count,
                "universal_candidate_count": universal_result.candidate_count,
                "merged_candidate_count": len(merged_facts),
                "strategy": "primary_plus_universal_raw",
            },
        )

        return self._structure_or_defer_llm_if_needed(
            text=text,
            raw_result=raw_result,
            document_type=resolved_document_type,
            strategy="primary_plus_universal_with_quality_gate",
        )

    def _structure_or_defer_llm_if_needed(
        self,
        text: str,
        raw_result: ExtractionResult,
        document_type: str,
        strategy: str,
    ) -> ExtractionResult:
        if not raw_result.succeeded:
            return raw_result

        gated_facts = filter_candidate_facts(list(raw_result.candidate_facts))
        llm_needed = _needs_llm_cleanup(
            document_type=document_type,
            text=text,
            candidate_count=raw_result.candidate_count,
            quality_count=len(gated_facts),
        )

        metadata = {
            **raw_result.metadata,
            "strategy": strategy,
            "raw_candidate_count": raw_result.candidate_count,
            "quality_gate_candidate_count": len(gated_facts),
            "llm_cleanup_triggered": False,
            "llm_cleanup_pending": bool(llm_needed),
            "llm_cleanup_reason": "noise_detected_after_ocr" if llm_needed else "",
            "review_source": "ocr",
        }

        return ExtractionResult.success(
            document_id=raw_result.document_id,
            source_id=raw_result.source_id,
            extractor_id=raw_result.extractor_id,
            candidate_facts=tuple(gated_facts),
            metadata=metadata,
        )

    def _apply_quality_gate(
        self,
        result: ExtractionResult,
        strategy: str,
    ) -> ExtractionResult:
        if not result.succeeded:
            return result

        original_count = result.candidate_count
        gated_facts = filter_candidate_facts(list(result.candidate_facts))

        return ExtractionResult.success(
            document_id=result.document_id,
            source_id=result.source_id,
            extractor_id=result.extractor_id,
            candidate_facts=tuple(gated_facts),
            metadata={
                **result.metadata,
                "strategy": strategy,
                "raw_candidate_count": original_count,
                "quality_gate_candidate_count": len(gated_facts),
            },
        )

    def _structure_or_fallback(
        self,
        request: ExtractionRequest,
        text: str,
        raw_result: ExtractionResult,
    ) -> ExtractionResult:
        if not raw_result.succeeded or raw_result.is_empty:
            return raw_result

        try:
            if self._llm_structurer is None:
                self._llm_structurer = LLMExtractionStructurer(make_extraction_llm())

            structured = self._llm_structurer.structure(
                request=request,
                raw_text=text,
                candidates=list(raw_result.candidate_facts),
            )

            if structured.succeeded and not structured.is_empty:
                merged_facts = _merge_candidate_facts(
                    list(raw_result.candidate_facts),
                    list(structured.candidate_facts),
                )
                structured_facts = filter_candidate_facts(merged_facts)

                return ExtractionResult.success(
                    document_id=raw_result.document_id,
                    source_id=raw_result.source_id,
                    extractor_id=ExtractorId(
                        f"{raw_result.extractor_id}+llm_structured"
                    ),
                    candidate_facts=tuple(structured_facts),
                    metadata={
                        **raw_result.metadata,
                        "strategy": "extract_then_llm_cleanup_with_quality_gate",
                        "raw_candidate_count": raw_result.candidate_count,
                        "structured_candidate_count": structured.candidate_count,
                        "merged_with_llm_candidate_count": len(merged_facts),
                        "quality_gate_candidate_count": len(structured_facts),
                        "llm_cleanup_triggered": True,
                        "llm_structuring_succeeded": True,
                        "llm_cleanup_pending": False,
                        "review_source": "llm",
                    },
                )

            _log.warning(
                "LLM structuring did not produce usable facts, falling back to raw extraction"
            )
            return self._apply_quality_gate(
                raw_result.with_metadata("llm_structuring_succeeded", False),
                "llm_fallback_quality_gate",
            )

        except Exception as exc:
            _log.exception("LLM structuring crashed, falling back to raw extraction")
            return self._apply_quality_gate(
                raw_result.with_metadata("llm_structuring_error", str(exc)),
                "llm_error_quality_gate",
            )


def _merge_candidate_facts(
    primary: list[CandidateFact],
    universal: list[CandidateFact],
) -> list[CandidateFact]:
    seen: set[tuple[str, str]] = set()
    result: list[CandidateFact] = []

    for fact in [*primary, *universal]:
        key = (
            str(fact.fact_type).strip().lower(),
            str(fact.normalized_value).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)

    return result
