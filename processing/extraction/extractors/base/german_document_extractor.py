from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from core.guards import require
from core.types import (
    DocumentId,
    EntityId,
    ExtractorId,
    SourceId,
    SpanId,
)
from processing.extraction.candidate_fact import CandidateFact
from processing.extraction.extractable_content import ExtractableContent
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.extraction.extractors.base.german_dates import (
    GermanDateParseResult,
    validate_birth_date,
    validate_expiry_date,
)
from processing.extraction.extractors.base.mrz_parser import (
    MrzParseResult,
    parse_text,
)
from processing.extraction.spatial_data import ExtractableSpan

_log = logging.getLogger(__name__)

_DE_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})[.\-/](?P<month>\d{1,2})[.\-/](?P<year>\d{4})\b"
)
_DE_NUMBER_RE = re.compile(
    r"\b(?P<integer>(?:\d{1,3})(?:\.\d{3})*)(?:,(?P<decimal>\d+))?\b"
)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_DE_MONTH_NAMES: dict[str, str] = {
    "januar": "01",
    "jan": "01",
    "februar": "02",
    "feb": "02",
    "märz": "03",
    "maerz": "03",
    "mrz": "03",
    "april": "04",
    "apr": "04",
    "mai": "05",
    "juni": "06",
    "jun": "06",
    "juli": "07",
    "jul": "07",
    "august": "08",
    "aug": "08",
    "september": "09",
    "sep": "09",
    "sept": "09",
    "oktober": "10",
    "okt": "10",
    "november": "11",
    "nov": "11",
    "dezember": "12",
    "dez": "12",
}

_DEFAULT_PIVOT: int = 30


class GermanDocumentExtractor(ABC):

    @property
    @abstractmethod
    def extractor_id(self) -> ExtractorId: ...

    @property
    @abstractmethod
    def supported_document_types(self) -> frozenset[str]: ...

    def can_handle(self, request: ExtractionRequest) -> bool:
        doc_type = request.content.document_type
        if doc_type is None:
            return False
        return doc_type.lower() in self.supported_document_types

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        require(
            isinstance(request, ExtractionRequest),
            "request must be an ExtractionRequest",
        )
        content = request.content
        document_id = content.document_id
        source_id = content.source_id
        try:
            facts = self._extract(request)
            return self._success(document_id, source_id, facts)
        except Exception as exc:
            _log.exception(
                "extractor %r failed on document %r: %s",
                self.extractor_id,
                document_id,
                exc,
            )
            return self._failure(document_id, source_id, reason=str(exc))

    @abstractmethod
    def _extract(self, request: ExtractionRequest) -> tuple[CandidateFact, ...]: ...

    def _content(self, request: ExtractionRequest) -> ExtractableContent:
        return request.content

    def _text(self, request: ExtractionRequest) -> str:
        return request.content.normalized_text

    def _spans(self, request: ExtractionRequest) -> tuple[ExtractableSpan, ...]:
        return request.content.all_spans

    def _find_spans(
        self,
        request: ExtractionRequest,
        query: str,
        *,
        case_sensitive: bool = False,
    ) -> tuple[ExtractableSpan, ...]:
        return request.content.find_by_text(query, case_sensitive=case_sensitive)

    def _parse_mrz(self, text: str) -> MrzParseResult:
        return parse_text(text)

    def _validate_birth_date(
        self,
        value: str,
        pivot_year: int = _DEFAULT_PIVOT,
    ) -> GermanDateParseResult:
        return validate_birth_date(value, pivot_year)

    def _validate_expiry_date(
        self,
        value: str,
        pivot_year: int = _DEFAULT_PIVOT,
    ) -> GermanDateParseResult:
        return validate_expiry_date(value, pivot_year)

    def _make_candidate_fact(
        self,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        fact_type: str,
        source_stage: str,
        raw_value: str,
        normalized_value: str,
        confidence: float,
        span_ids: tuple[SpanId, ...],
        metadata: dict[str, Any] | None = None,
    ) -> CandidateFact:
        return CandidateFact.create(
            document_id=document_id,
            source_id=source_id,
            entity_id=entity_id,
            fact_type=fact_type,
            source_stage=source_stage,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=round(max(0.0, min(1.0, confidence)), 4),
            span_ids=span_ids,
            metadata=metadata,
        )

    def _normalize_whitespace(self, text: str) -> str:
        text = _MULTI_SPACE_RE.sub(" ", text)
        text = _MULTI_NEWLINE_RE.sub("\n\n", text)
        return text.strip()

    def _normalize_german_date(self, raw: str) -> str | None:
        raw = raw.strip()
        m = _DE_DATE_RE.match(raw)
        if m:
            day = m.group("day").zfill(2)
            month = m.group("month").zfill(2)
            year = m.group("year")
            return f"{year}-{month}-{day}"
        lower = raw.lower()
        for name, num in _DE_MONTH_NAMES.items():
            pattern = re.compile(
                rf"\b(?P<day>\d{{1,2}})\s*\.?\s*{re.escape(name)}\s*\.?\s*(?P<year>\d{{4}})\b",
                re.IGNORECASE,
            )
            match = pattern.search(lower)
            if match:
                day = match.group("day").zfill(2)
                year = match.group("year")
                return f"{year}-{num}-{day}"
        return None

    def _normalize_german_number(self, raw: str) -> float | None:
        raw = raw.strip()
        m = _DE_NUMBER_RE.fullmatch(raw)
        if not m:
            return None
        integer_part = m.group("integer").replace(".", "")
        decimal_part = m.group("decimal") or "0"
        try:
            return float(f"{integer_part}.{decimal_part}")
        except ValueError:
            return None

    def _combine_confidence(self, confidences: Iterable[float]) -> float:
        values = list(confidences)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)

    def _success(
        self,
        document_id: DocumentId,
        source_id: SourceId,
        facts: tuple[CandidateFact, ...],
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        return ExtractionResult.success(
            document_id=document_id,
            source_id=source_id,
            extractor_id=self.extractor_id,
            candidate_facts=facts,
            metadata=metadata,
        )

    def _failure(
        self,
        document_id: DocumentId,
        source_id: SourceId,
        *,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        base_meta: dict[str, Any] = {"reason": reason}
        if metadata:
            base_meta.update(metadata)
        return ExtractionResult.failure(
            document_id=document_id,
            source_id=source_id,
            extractor_id=self.extractor_id,
            metadata=base_meta,
        )
