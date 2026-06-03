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

_EXTRACTOR_ID: ExtractorId = ExtractorId("de.payslip.v1")
_SOURCE_STAGE: str = "extraction:payslip"
_SUPPORTED: frozenset[str] = frozenset(
    {
        "payslip",
        "lohnabrechnung",
        "gehaltsabrechnung",
        "lohnzettel",
    }
)

_ALL_FACT_TYPES: frozenset[str] = frozenset(
    {
        "employer_name",
        "employee_name",
        "employee_id",
        "tax_id",
        "social_security_number",
        "pay_period_start",
        "pay_period_end",
        "pay_month",
        "pay_date",
        "gross_salary",
        "annual_gross_salary",
        "net_salary",
        "annual_net_salary",
        "bonus",
        "tax_class",
        "income_tax",
        "solidarity_surcharge",
        "church_tax",
        "health_insurance",
        "pension_contribution",
        "unemployment_insurance",
        "care_insurance",
    }
)

_CONF_HIGH: float = 0.90
_CONF_MEDIUM: float = 0.75
_CONF_LOW: float = 0.55

_DATE_FACT_TYPES: frozenset[str] = frozenset(
    {
        "pay_period_start",
        "pay_period_end",
        "pay_date",
    }
)

_MONETARY_FACT_TYPES: frozenset[str] = frozenset(
    {
        "gross_salary",
        "annual_gross_salary",
        "net_salary",
        "annual_net_salary",
        "bonus",
        "income_tax",
        "solidarity_surcharge",
        "church_tax",
        "health_insurance",
        "pension_contribution",
        "unemployment_insurance",
        "care_insurance",
    }
)

_MONTH_MAP: dict[str, str] = {
    "januar": "01",
    "january": "01",
    "jan": "01",
    "februar": "02",
    "february": "02",
    "feb": "02",
    "märz": "03",
    "maerz": "03",
    "march": "03",
    "mar": "03",
    "april": "04",
    "apr": "04",
    "mai": "05",
    "may": "05",
    "juni": "06",
    "june": "06",
    "jun": "06",
    "juli": "07",
    "july": "07",
    "jul": "07",
    "august": "08",
    "aug": "08",
    "september": "09",
    "sep": "09",
    "oktober": "10",
    "october": "10",
    "oct": "10",
    "okt": "10",
    "november": "11",
    "nov": "11",
    "dezember": "12",
    "december": "12",
    "dec": "12",
    "dez": "12",
}


def _amount_normalize(raw: str) -> str:
    cleaned = raw.strip().replace("\xa0", "").replace(" ", "")
    if re.search(r"\d\.\d{3},", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.search(r"\d,\d{3}\.", cleaned):
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return raw.strip()


def _pay_month_normalize(raw: str) -> tuple[str, str] | None:
    s = raw.strip()

    full = re.match(r"^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$", s)
    if full:
        d, m, y = full.group(1), full.group(2), full.group(3)
        return f"{y}-{int(m):02d}-{int(d):02d}", "full_date"

    num_month = re.match(r"^(\d{1,2})[.\-/](\d{4})$", s)
    if num_month:
        m, y = num_month.group(1), num_month.group(2)
        return f"{y}-{int(m):02d}-01", "numeric_month_start"

    word_month = re.match(r"^(\w+)\s+(\d{4})$", s, re.IGNORECASE)
    if word_month:
        month_key = word_month.group(1).lower()
        year = word_month.group(2)
        month_num = _MONTH_MAP.get(month_key)
        if month_num:
            return f"{year}-{month_num}-01", "month_start_inferred"

    return None


def _sv_number_normalize(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def _sv_number_valid(normalized: str) -> bool:
    return bool(
        re.match(r"^\d{2}[0-3]\d[0-1]\d[A-Z]\d{3}$", normalized)
        or re.match(r"^[A-Z]\d{8}[A-Z]\d{2}$", normalized)
    )


_MONETARY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "gross_salary",
        re.compile(
            r"(?:bruttogehalt|bruttolohn|brutto(?:\s+gesamt)?|gross\s+salary)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "annual_gross_salary",
        re.compile(
            r"(?:jahresbrutto|jahres(?:brutto)?gehalt|annual\s+gross)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "net_salary",
        re.compile(
            r"(?:nettolohn|nettogehalt|netto(?:\s+gesamt)?|auszahlungsbetrag|"
            r"net\s+(?:salary|pay))"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "annual_net_salary",
        re.compile(
            r"(?:jahresnetto|jahres(?:netto)?gehalt|annual\s+net)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "bonus",
        re.compile(
            r"(?:sonderzahlung|prämie|bonus|gratifikation|weihnachtsgeld|urlaubsgeld)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "income_tax",
        re.compile(
            r"(?:lohnsteuer|einkommensteuer|income\s+tax)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "solidarity_surcharge",
        re.compile(
            r"(?:solidaritätszuschlag|soli(?:zuschlag)?)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "church_tax",
        re.compile(
            r"(?:kirchensteuer|church\s+tax)" r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "health_insurance",
        re.compile(
            r"(?:krankenversicherung|kv(?:\s+beitrag)?|health\s+insurance)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "pension_contribution",
        re.compile(
            r"(?:rentenversicherung|rv(?:\s+beitrag)?|pension(?:\s+contribution)?)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "unemployment_insurance",
        re.compile(
            r"(?:arbeitslosenversicherung|av(?:\s+beitrag)?|unemployment(?:\s+insurance)?)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
    (
        "care_insurance",
        re.compile(
            r"(?:pflegeversicherung|pv(?:\s+beitrag)?|care\s+insurance)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro)?",
            re.IGNORECASE,
        ),
    ),
]

_MONETARY_BOUNDS: dict[str, tuple[float, float]] = {
    "gross_salary": (100.0, 50_000.0),
    "annual_gross_salary": (1_200.0, 600_000.0),
    "net_salary": (100.0, 40_000.0),
    "annual_net_salary": (1_200.0, 480_000.0),
    "bonus": (1.0, 100_000.0),
    "income_tax": (0.0, 20_000.0),
    "solidarity_surcharge": (0.0, 1_000.0),
    "church_tax": (0.0, 2_000.0),
    "health_insurance": (0.0, 2_000.0),
    "pension_contribution": (0.0, 2_000.0),
    "unemployment_insurance": (0.0, 500.0),
    "care_insurance": (0.0, 500.0),
}


def _sanity_check_amount(fact_type: str, normalized: str) -> tuple[bool, float]:
    bounds = _MONETARY_BOUNDS.get(fact_type)
    if bounds is None:
        return True, _CONF_HIGH
    try:
        value = float(normalized)
    except ValueError:
        return False, _CONF_LOW
    lo, hi = bounds
    if value < lo or value > hi:
        return False, _CONF_LOW
    return True, _CONF_HIGH


_OCR_LABEL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "employer_name": [
        re.compile(
            r"(?:arbeitgeber|employer|firma|unternehmen)[:\s]+([^\n,]{2,80})",
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
    ],
    "employee_id": [
        re.compile(
            r"(?:personalnummer|mitarbeiternummer|employee\s*(?:id|number|nr\.?))"
            r"[:\s]+([A-Z0-9\-]{2,20})",
            re.IGNORECASE,
        ),
    ],
    "tax_id": [
        re.compile(
            r"(?:steuer(?:identifikationsnummer|id(?:nummer)?)|steuer-?id|tax\s*id)"
            r"[:\s]+(\d[\d\s]{9,12})",
            re.IGNORECASE,
        ),
    ],
    "social_security_number": [
        re.compile(
            r"(?:sozialversicherungsnummer|sv(?:\s*-?\s*nummer)?|"
            r"rentenversicherungsnummer|social\s+security)"
            r"[:\s]+([\d\s]{2}\s?[\d\s]{6}\s?[A-Za-z]\s?[\d\s]{3})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:sozialversicherungsnummer|sv(?:\s*-?\s*nummer)?)"
            r"[:\s]+([A-Za-z][\d\s]{8}[A-Za-z][\d\s]{2})",
            re.IGNORECASE,
        ),
    ],
    "pay_period_start": [
        re.compile(
            r"(?:abrechnungszeitraum|pay(?:roll)?\s+period|lohnzeitraum)"
            r"[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:von|from)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})"
            r"(?=\s*(?:bis|to)\s+\d)",
            re.IGNORECASE,
        ),
    ],
    "pay_period_end": [
        re.compile(
            r"(?:abrechnungszeitraum|pay(?:roll)?\s+period|lohnzeitraum)"
            r"[:\s]+\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}"
            r"\s*(?:bis|to|–|-)\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:bis|to)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "pay_month": [
        re.compile(
            r"(?:für\s+(?:den\s+)?monat|for\s+(?:the\s+)?month\s+of|monat)[:\s]+"
            r"(\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:für\s+(?:den\s+)?monat|for\s+(?:the\s+)?month\s+of|monat)[:\s]+"
            r"([A-Za-zÄÖÜäöü]+\s+\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:lohnabrechnung|gehaltsabrechnung)\s+"
            r"([A-Za-zÄÖÜäöü]+\s+\d{4}|\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "pay_date": [
        re.compile(
            r"(?:auszahlungsdatum|zahlungsdatum|pay(?:ment)?\s+date|überweisungsdatum)"
            r"[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "tax_class": [
        re.compile(
            r"(?:steuerklasse|steuerkl\.?|tax\s+class)" r"[:\s]+([1-6](?:/[1-6])?)",
            re.IGNORECASE,
        ),
    ],
}


def _span_ids_for(
    spans: tuple[ExtractableSpan, ...],
    query: str,
    context: str,
) -> tuple[SpanId, ...]:
    matched = tuple(s.span_id for s in spans if query.upper() in s.text.upper())
    if matched:
        return matched
    _log.warning(
        "payslip extractor: no span matched %r for %r — fact retained with empty span_ids",
        query,
        context,
    )
    return ()


class PayslipExtractor(GermanDocumentExtractor):

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
            self._extract_monetary(
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

    def _extract_monetary(
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

        for fact_type, pattern in _MONETARY_PATTERNS:
            if fact_type not in requested:
                continue
            match = pattern.search(text)
            if not match:
                continue
            raw = match.group(1).strip()
            if not raw:
                continue

            normalized = _amount_normalize(raw)
            sane, confidence = _sanity_check_amount(fact_type, normalized)
            span_ids = _span_ids_for(spans, raw, fact_type)

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
                    metadata={
                        "source": "ocr_label",
                        "currency": "EUR",
                        "sanity_passed": sane,
                    },
                )
            )

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

                elif fact_type == "pay_month":
                    parsed = _pay_month_normalize(raw)
                    if parsed is not None:
                        normalized, resolution = parsed
                        extra_meta["resolution"] = resolution
                        extra_meta["date_valid"] = True
                        confidence = (
                            _CONF_HIGH
                            if resolution in ("full_date", "numeric_month_start")
                            else _CONF_MEDIUM
                        )
                    else:
                        normalized = raw
                        extra_meta["date_valid"] = False
                        confidence = _CONF_LOW

                elif fact_type == "tax_class":
                    normalized = raw.strip()
                    confidence = _CONF_HIGH

                elif fact_type == "tax_id":
                    normalized = re.sub(r"\s+", "", raw)
                    extra_meta["digits"] = len(normalized)
                    confidence = _CONF_HIGH if len(normalized) == 11 else _CONF_LOW

                elif fact_type == "social_security_number":
                    normalized = _sv_number_normalize(raw)
                    valid = _sv_number_valid(normalized)
                    extra_meta["format_valid"] = valid
                    confidence = _CONF_HIGH if valid else _CONF_LOW

                elif fact_type == "employee_id":
                    normalized = raw.strip().upper()
                    confidence = _CONF_HIGH

                elif fact_type == "employee_name":
                    normalized = self._normalize_whitespace(raw)
                    confidence = _CONF_MEDIUM

                else:
                    normalized = self._normalize_whitespace(raw)

                span_ids = _span_ids_for(spans, raw, fact_type)

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
