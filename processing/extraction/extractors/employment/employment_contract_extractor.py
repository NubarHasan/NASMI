from __future__ import annotations

import logging
import re
from typing import Any

from core.types import (
    DocumentId,
    EntityId,
    ExtractorId,
    SourceId,
    SpanId,
)
from processing.extraction.candidate_fact import CandidateFact
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extractors.base.german_dates import try_parse_date
from processing.extraction.extractors.base.german_document_extractor import (
    GermanDocumentExtractor,
)
from processing.extraction.spatial_data import ExtractableSpan

_log = logging.getLogger(__name__)

_EXTRACTOR_ID: ExtractorId = ExtractorId("de.employment_contract.v1")
_SOURCE_STAGE: str = "extraction:employment_contract"
_SUPPORTED: frozenset[str] = frozenset(
    {
        "employment_contract",
        "arbeitsvertrag",
    }
)

_ALL_FACT_TYPES: frozenset[str] = frozenset(
    {
        "employer_name",
        "employer_address",
        "employee_name",
        "employment_start_date",
        "employment_end_date",
        "employment_type",
        "job_title",
        "working_hours",
        "salary_amount",
        "salary_currency",
        "salary_interval",
        "probation_end_date",
        "probation_duration_months",
        "notice_period",
        "collective_agreement",
        "workplace_location",
    }
)

_CONF_HIGH: float = 0.90
_CONF_MEDIUM: float = 0.75
_CONF_LOW: float = 0.55

_CURRENCY_MAP: dict[str, str] = {
    "euro": "EUR",
    "eur": "EUR",
    "€": "EUR",
    "chf": "CHF",
    "usd": "USD",
    "$": "USD",
    "£": "GBP",
    "gbp": "GBP",
}

_INTERVAL_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"monat|monthly|pro\s+monat", re.IGNORECASE), "monthly"),
    (re.compile(r"jahr|annual|jährlich|pro\s+jahr", re.IGNORECASE), "annual"),
    (re.compile(r"woche|weekly|wöchentlich|pro\s+woche", re.IGNORECASE), "weekly"),
    (re.compile(r"stunde|hourly|stündlich|pro\s+stunde", re.IGNORECASE), "hourly"),
]

_EMPLOYMENT_TYPE_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"unbefristet|permanent", re.IGNORECASE), "permanent"),
    (re.compile(r"befristet|fixed.term|temporary", re.IGNORECASE), "fixed_term"),
    (re.compile(r"teilzeit|part.time", re.IGNORECASE), "part_time"),
    (re.compile(r"vollzeit|full.time", re.IGNORECASE), "full_time"),
    (re.compile(r"minijob|geringfügig", re.IGNORECASE), "minijob"),
    (
        re.compile(r"ausbildung|ausbildungsvertrag|apprenticeship", re.IGNORECASE),
        "apprenticeship",
    ),
    (re.compile(r"praktikum|internship", re.IGNORECASE), "internship"),
    (re.compile(r"werkvertrag", re.IGNORECASE), "service_contract"),
    (re.compile(r"freier?\s+mitarbeiter|freelance", re.IGNORECASE), "freelance"),
]

# ---------------------------------------------------------------------------
# Salary — single-pass patterns that capture amount + optional currency + optional interval
# ---------------------------------------------------------------------------

_SALARY_FULL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:gehalt|lohn|vergütung|brutto(?:gehalt|lohn)?|grundgehalt|salary|remuneration)"
        r"[:\s]+"
        r"([\d.,]+)"
        r"\s*(€|EUR|euro|CHF|USD|\$|£|GBP)?"
        r"\s*(monatlich|monthly|jährlich|annual|wöchentlich|weekly|stündlich|hourly"
        r"|pro\s+monat|pro\s+jahr|pro\s+woche|pro\s+stunde)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"([\d.,]+)"
        r"\s*(€|EUR|euro|CHF|USD|\$|£|GBP)"
        r"\s*(monatlich|monthly|jährlich|annual|wöchentlich|weekly|stündlich|hourly"
        r"|pro\s+monat|pro\s+jahr|pro\s+woche|pro\s+stunde|brutto|gross)?",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# Probation — separated: date vs duration
# ---------------------------------------------------------------------------

_PROBATION_DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:probezeit(?:\s+endet|\s+bis)?|probation(?:ary)?\s+(?:period\s+)?(?:ends?|until)?)"
        r"[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
        re.IGNORECASE,
    ),
]

_PROBATION_DURATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"probezeit\s+(?:beträgt|von|:)\s*(\d+)\s*(?:monat(?:en?)?|month)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+)[\s-]*(?:monatige|monatliche)\s+probezeit",
        re.IGNORECASE,
    ),
    re.compile(
        r"probation(?:ary)?\s+period\s+(?:of\s+)?(\d+)\s*month",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# OCR label patterns (non-salary, non-probation)
# ---------------------------------------------------------------------------

_OCR_LABEL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "employer_name": [
        re.compile(
            r"(?:arbeitgeber|employer|firma|unternehmen|gesellschaft)[:\s]+([^\n,]{2,80})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:zwischen\s+(?:der\s+)?(?:firma\s+)?)([A-ZÄÖÜ][^\n,]{2,60})"
            r"(?:\s*,|\s+und\b|\s+and\b|\s+\()",
            re.IGNORECASE,
        ),
    ],
    "employer_address": [
        re.compile(
            r"(?:arbeitgeber(?:adresse|anschrift)|employer\s+address)[:\s]+([^\n]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"([A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\s\-]+"
            r"(?:straße|str\.|gasse|weg|allee|platz|ring)"
            r"\s+\d+[a-z]?\s*,?\s*\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+)",
            re.IGNORECASE,
        ),
    ],
    "employee_name": [
        re.compile(
            r"(?:arbeitnehmer(?:in)?|mitarbeiter(?:in)?|employee)"
            r"[:\s]+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:herr(?:n)?|frau)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:und\s+(?:herrn?\s+|frau\s+)?|and\s+(?:mr\.?\s+|ms\.?\s+|mrs\.?\s+)?)"
            r"([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+)",
            re.IGNORECASE,
        ),
        # zwischen Firma XYZ \n und \n Max Mustermann
        re.compile(
            r"und\s*\n\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+)",
            re.IGNORECASE,
        ),
    ],
    "employment_start_date": [
        re.compile(
            r"(?:beginn(?:\s+des\s+(?:arbeits(?:verhältnisses|vertrags?))?)?|"
            r"eintrittsdatum|start(?:\s+date)?|ab\s+dem)[:\s]+"
            r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:zum|ab|starting|commencing)\s+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "employment_end_date": [
        re.compile(
            r"(?:ende(?:\s+des\s+(?:arbeits(?:verhältnisses|vertrags?))?)?|"
            r"befristet\s+bis|end(?:\s+date)?|bis\s+zum)[:\s]+"
            r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "employment_type": [
        re.compile(
            r"(?:art\s+(?:des\s+)?(?:arbeits(?:verhältnisses|vertrags?)|beschäftigung)|"
            r"employment\s+type|beschäftigungsart)[:\s]+([^\n.]{2,80})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(unbefristete[sr]?\s+arbeitsvertrag|befristete[sr]?\s+arbeitsvertrag|"
            r"teilzeit(?:beschäftigung)?|vollzeit(?:beschäftigung)?|"
            r"minijob|ausbildungsvertrag|praktikumsvertrag|werkvertrag)",
            re.IGNORECASE,
        ),
    ],
    "job_title": [
        re.compile(
            r"(?:position|stelle|tätigkeit|berufsbezeichnung|job\s*title|funktion)"
            r"[:\s]+([^\n.]{2,80})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:eingestellt\s+als|hired\s+as|tätig\s+als)\s+([^\n.]{2,80})",
            re.IGNORECASE,
        ),
    ],
    "working_hours": [
        re.compile(
            r"(?:arbeitszeit|wochenarbeitszeit|working\s+hours?|stunden\s+pro\s+woche)"
            r"[:\s]+(\d+(?:[.,]\d+)?)\s*(?:stunden?|std\.?|hours?|h)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:stunden?|std\.?)\s*(?:pro|je|per)\s*woche",
            re.IGNORECASE,
        ),
    ],
    "notice_period": [
        re.compile(
            r"(?:kündigungsfrist|notice\s+period)[:\s]+([^\n.]{2,60})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:kündigung\s+(?:ist\s+)?(?:mit|mit\s+einer\s+frist\s+von))\s+([^\n.]{2,60})",
            re.IGNORECASE,
        ),
    ],
    "collective_agreement": [
        re.compile(
            r"(?:tarifvertrag|tarifliche\s+regelung|collective\s+agreement|"
            r"tarifgruppe|entgeltgruppe)[:\s]+([^\n.]{2,80})",
            re.IGNORECASE,
        ),
    ],
    "workplace_location": [
        re.compile(
            r"(?:arbeitsort|einsatzort|dienstort|workplace|place\s+of\s+work|"
            r"tätigkeitsort)[:\s]+([^\n.]{2,80})",
            re.IGNORECASE,
        ),
    ],
}

_DATE_FACT_TYPES: frozenset[str] = frozenset(
    {
        "employment_start_date",
        "employment_end_date",
        "probation_end_date",
    }
)


def _currency_normalize(raw: str) -> str:
    return _CURRENCY_MAP.get(raw.strip().lower(), raw.strip().upper())


def _interval_normalize(raw: str) -> str:
    for pattern, normalized in _INTERVAL_MAP:
        if pattern.search(raw):
            return normalized
    return raw.strip().lower()


def _employment_type_normalize(raw: str) -> str:
    for pattern, normalized in _EMPLOYMENT_TYPE_MAP:
        if pattern.search(raw):
            return normalized
    return raw.strip().lower().replace(" ", "_")


def _salary_normalize(raw: str) -> str:
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return raw.strip()


def _working_hours_normalize(raw: str) -> str:
    try:
        return f"{float(raw.strip().replace(',', '.')):.1f}"
    except ValueError:
        return raw.strip()


def _span_ids_for(
    spans: tuple[ExtractableSpan, ...],
    query: str,
) -> tuple[SpanId, ...]:
    matched = tuple(s.span_id for s in spans if query.upper() in s.text.upper())
    return matched if matched else (spans[0].span_id,) if spans else ()


class EmploymentContractExtractor(GermanDocumentExtractor):

    @property
    def extractor_id(self) -> ExtractorId:
        return _EXTRACTOR_ID

    @property
    def supported_document_types(self) -> frozenset[str]:
        return _SUPPORTED

    def _extract(self, request: ExtractionRequest) -> tuple[CandidateFact, ...]:
        content = request.content
        text = content.raw_text
        spans = self._spans(request)
        document_id = content.document_id
        source_id = content.source_id
        entity_id = EntityId(content.document_id)
        requested = set(request.requested_fact_types) or set(_ALL_FACT_TYPES)
        facts: list[CandidateFact] = []

        facts.extend(
            self._extract_salary(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
            )
        )

        facts.extend(
            self._extract_probation(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
            )
        )

        already = {f.fact_type for f in facts}
        facts.extend(
            self._extract_from_ocr(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
                already_extracted=already,
            )
        )

        return tuple(facts)

    def _extract_salary(
        self,
        text: str,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        spans: tuple[ExtractableSpan, ...],
        requested: set[str],
    ) -> list[CandidateFact]:
        salary_targets = {
            "salary_amount",
            "salary_currency",
            "salary_interval",
        } & requested
        if not salary_targets:
            return []

        for pattern in _SALARY_FULL_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue

            raw_amount = match.group(1).strip() if match.lastindex is not None and match.lastindex >= 1 else ""
            raw_currency = (
                match.group(2).strip()
                if match.lastindex is not None and match.lastindex >= 2 and match.group(2)
                else ""
            )
            raw_interval = (
                match.group(3).strip()
                if match.lastindex is not None and match.lastindex >= 3 and match.group(3)
                else ""
            )

            if not raw_amount:
                continue

            span_ids = _span_ids_for(spans, raw_amount)
            if not span_ids:
                _log.debug(
                    "employment contract extractor: no span for salary amount %r",
                    raw_amount,
                )
                continue

            facts: list[CandidateFact] = []

            if "salary_amount" in salary_targets:
                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type="salary_amount",
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw_amount,
                        normalized_value=_salary_normalize(raw_amount),
                        confidence=_CONF_HIGH,
                        span_ids=span_ids,
                        metadata={"source": "ocr_label"},
                    )
                )

            if "salary_currency" in salary_targets and raw_currency:
                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type="salary_currency",
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw_currency,
                        normalized_value=_currency_normalize(raw_currency),
                        confidence=_CONF_HIGH,
                        span_ids=span_ids,
                        metadata={"source": "ocr_label"},
                    )
                )

            if "salary_interval" in salary_targets and raw_interval:
                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type="salary_interval",
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw_interval,
                        normalized_value=_interval_normalize(raw_interval),
                        confidence=_CONF_HIGH,
                        span_ids=span_ids,
                        metadata={"source": "ocr_label"},
                    )
                )

            return facts

        return []

    def _extract_probation(
        self,
        text: str,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        spans: tuple[ExtractableSpan, ...],
        requested: set[str],
    ) -> list[CandidateFact]:
        facts: list[CandidateFact] = []

        if "probation_end_date" in requested:
            for pattern in _PROBATION_DATE_PATTERNS:
                match = pattern.search(text)
                if not match:
                    continue
                raw = match.group(1).strip()
                result = try_parse_date(raw)
                norm = result.value.isoformat() if result.value is not None else raw
                conf = _CONF_HIGH if result.value is not None else _CONF_LOW
                span_ids = _span_ids_for(spans, raw)
                if not span_ids:
                    continue
                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type="probation_end_date",
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=conf,
                        span_ids=span_ids,
                        metadata={
                            "source": "ocr_label",
                            "date_valid": result.value is not None,
                        },
                    )
                )
                break

        if "probation_duration_months" in requested:
            for pattern in _PROBATION_DURATION_PATTERNS:
                match = pattern.search(text)
                if not match:
                    continue
                raw = match.group(1).strip()
                span_ids = _span_ids_for(spans, raw)
                if not span_ids:
                    continue
                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type="probation_duration_months",
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw,
                        normalized_value=raw,
                        confidence=_CONF_HIGH,
                        span_ids=span_ids,
                        metadata={"source": "ocr_label", "unit": "months"},
                    )
                )
                break

        return facts

    def _extract_from_ocr(
        self,
        text: str,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        spans: tuple[ExtractableSpan, ...],
        requested: set[str],
        already_extracted: set[str],
    ) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        targets: set[str] = requested - already_extracted

        for fact_type, patterns in _OCR_LABEL_PATTERNS.items():
            if fact_type not in targets:
                continue
            for pattern in patterns:
                match = pattern.search(text)
                if not match:
                    continue
                raw = match.group(1).strip()
                if not raw:
                    continue

                confidence = _CONF_MEDIUM
                extra_meta: dict[str, Any] = {"source": "ocr_label"}

                if fact_type in _DATE_FACT_TYPES:
                    result = try_parse_date(raw)
                    normalized = (
                        result.value.isoformat() if result.value is not None else raw
                    )
                    extra_meta["date_valid"] = result.value is not None
                    confidence = _CONF_HIGH if result.value is not None else _CONF_LOW

                elif fact_type == "employment_type":
                    normalized = _employment_type_normalize(raw)
                    confidence = _CONF_HIGH

                elif fact_type == "working_hours":
                    normalized = _working_hours_normalize(raw)
                    extra_meta["unit"] = "hours_per_week"
                    confidence = _CONF_HIGH

                else:
                    normalized = self._normalize_whitespace(raw)

                span_ids = _span_ids_for(spans, raw)
                if not span_ids:
                    _log.debug(
                        "employment contract extractor: no span matched %r for %r",
                        raw,
                        fact_type,
                    )
                    continue

                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type=fact_type,
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw,
                        normalized_value=normalized,
                        confidence=confidence,
                        span_ids=span_ids,
                        metadata=extra_meta,
                    )
                )
                break

        return facts
