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

_EXTRACTOR_ID: ExtractorId = ExtractorId("de.invoice.v1")
_SOURCE_STAGE: str = "extraction:invoice"
_SUPPORTED: frozenset[str] = frozenset(
    {
        "invoice",
        "rechnung",
        "gutschrift",
    }
)

_ALL_FACT_TYPES: frozenset[str] = frozenset(
    {
        "invoice_number",
        "invoice_date",
        "due_date",
        "seller_name",
        "seller_address",
        "seller_tax_id",
        "seller_vat_id",
        "buyer_name",
        "buyer_address",
        "subtotal",
        "vat_rate",
        "vat_amount",
        "total_amount",
        "currency",
        "payment_reference",
        "line_items_raw",
    }
)

_CONF_HIGH: float = 0.90
_CONF_MEDIUM: float = 0.75
_CONF_LOW: float = 0.55

_DATE_FACT_TYPES: frozenset[str] = frozenset(
    {
        "invoice_date",
        "due_date",
    }
)

_MONETARY_FACT_TYPES: frozenset[str] = frozenset(
    {
        "subtotal",
        "vat_amount",
        "total_amount",
    }
)

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

_INLINE_CURRENCY_RE: re.Pattern[str] = re.compile(
    r"(€|EUR|euro|CHF|USD|\$|£|GBP)",
    re.IGNORECASE,
)


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


def _vat_rate_normalize(raw: str) -> str:
    cleaned = raw.strip().replace(",", ".").replace("%", "").strip()
    try:
        return f"{float(cleaned):.1f}"
    except ValueError:
        return raw.strip()


def _currency_normalize(raw: str) -> str:
    return _CURRENCY_MAP.get(raw.strip().lower(), raw.strip().upper())


def _vat_id_normalize(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def _tax_id_normalize(raw: str) -> str:
    return re.sub(r"[\s/]", "", raw)


def _detect_currency(text: str) -> str | None:
    match = _INLINE_CURRENCY_RE.search(text)
    if match:
        return _currency_normalize(match.group(1))
    return None


_MONETARY_BOUNDS: dict[str, tuple[float, float]] = {
    "subtotal": (0.0, 10_000_000.0),
    "vat_amount": (0.0, 2_000_000.0),
    "total_amount": (0.0, 10_000_000.0),
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


_MONETARY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "subtotal",
        re.compile(
            r"(?:nettobetrag|netto(?:\s+gesamt)?|zwischensumme|subtotal|"
            r"betrag\s+(?:ohne|vor)\s+(?:mwst|ust|steuer))"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
    (
        "vat_amount",
        re.compile(
            r"(?:mehrwertsteuer(?:betrag)?|mwst(?:\s+betrag)?|"
            r"umsatzsteuer(?:betrag)?|ust(?:\s+betrag)?|vat\s+amount|tax\s+amount)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
    (
        "total_amount",
        re.compile(
            r"(?:gesamtbetrag|rechnungsbetrag|endbetrag|zu\s+zahlender?\s+betrag|"
            r"total(?:\s+amount)?|bruttobetrag|gesamt(?:\s+inkl\.?\s+(?:mwst|ust))?)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
]

_LINE_ITEMS_START: list[re.Pattern[str]] = [
    re.compile(
        r"(?:pos(?:ition)?|beschreibung|leistung|artikel|description|item)"
        r"\s+(?:menge|anzahl|qty|quantity)?\s*(?:preis|price|betrag|amount)?",
        re.IGNORECASE,
    ),
]

_LINE_ITEMS_END: list[re.Pattern[str]] = [
    re.compile(
        r"(?:nettobetrag|zwischensumme|subtotal|gesamt|total|mwst|ust|mehrwertsteuer)",
        re.IGNORECASE,
    ),
]

_OCR_LABEL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "invoice_number": [
        re.compile(
            r"(?:rechnungsnummer|rechnungs-?nr\.?|invoice\s*(?:number|no\.?|#))"
            r"[:\s]+([A-Z0-9\-/_.]{2,40})",
            re.IGNORECASE,
        ),
    ],
    "invoice_date": [
        re.compile(
            r"(?:rechnungsdatum|invoice\s+date|datum)[:\s]+"
            r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "due_date": [
        re.compile(
            r"(?:fälligkeitsdatum|fällig\s+(?:am|bis)|zahlungsziel|due\s+(?:date|by))"
            r"[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:zahlbar\s+(?:bis|innerhalb)|zu\s+zahlen\s+bis)"
            r"[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "seller_name": [
        re.compile(
            r"(?:verkäufer|lieferant|anbieter|rechnungssteller|seller|vendor|from)"
            r"[:\s]+([^\n,]{2,80})",
            re.IGNORECASE,
        ),
    ],
    "seller_address": [
        re.compile(
            r"(?:verkäufer(?:adresse)?|lieferantenadresse|seller\s+address)"
            r"[:\s]+([^\n]+(?:\n[^\n]+){0,4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"([A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\s\-]+"
            r"(?:straße|str\.|gasse|weg|allee|platz|ring)"
            r"\s+\d+[a-z]?\s*,?\s*\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+)",
            re.IGNORECASE,
        ),
    ],
    "seller_tax_id": [
        re.compile(
            r"(?:steuernummer|st(?:euer)?\.?\s*nr\.?|tax\s+(?:number|id))"
            r"[:\s]+(\d[\d\s/]{8,14})",
            re.IGNORECASE,
        ),
    ],
    "seller_vat_id": [
        re.compile(
            r"(?:ust(?:\.?-?id(?:nr\.?)?)?|umsatzsteuer(?:identifikationsnummer)?|"
            r"vat(?:\s*(?:id|number|no\.?))?)"
            r"[:\s]+([A-Z]{2}[\d\s]{8,12})",
            re.IGNORECASE,
        ),
    ],
    "buyer_name": [
        re.compile(
            r"(?:käufer|auftraggeber|kunde|rechnungsempfänger|buyer|bill(?:ed)?\s+to|"
            r"rechnung\s+an)"
            r"[:\s]+([^\n,]{2,80})",
            re.IGNORECASE,
        ),
    ],
    "buyer_address": [
        re.compile(
            r"(?:käufer(?:adresse)?|lieferadresse|rechnungsadresse|"
            r"buyer\s+address|bill(?:ing)?\s+address)"
            r"[:\s]+([^\n]+(?:\n[^\n]+){0,4})",
            re.IGNORECASE,
        ),
    ],
    "vat_rate": [
        re.compile(
            r"(?:mwst(?:\s*-?\s*satz)?|ust(?:\s*-?\s*satz)?|"
            r"mehrwertsteuersatz|vat\s+rate|tax\s+rate)"
            r"[:\s]+(\d{1,2}(?:[.,]\d{1,2})?)\s*%?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%\s*"
            r"(?:mwst|ust|mehrwertsteuer|umsatzsteuer|vat)",
            re.IGNORECASE,
        ),
    ],
    "currency": [
        re.compile(
            r"(?:währung|currency)[:\s]+(€|EUR|euro|CHF|USD|\$|£|GBP)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:gesamtbetrag|total(?:\s+amount)?|rechnungsbetrag)"
            r"[^\n]{0,40}(€|EUR|euro|CHF|USD|\$|£|GBP)",
            re.IGNORECASE,
        ),
    ],
    "payment_reference": [
        re.compile(
            r"(?:verwendungszweck|zahlungsreferenz|referenz(?:nummer)?|"
            r"payment\s+reference|reference\s+(?:number|no\.?))"
            r"[:\s]+([^\n]{2,80})",
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
        "invoice extractor: no span matched %r for %r — fact retained with empty span_ids",
        query,
        context,
    )
    return ()


class InvoiceExtractor(GermanDocumentExtractor):

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

        detected_currency = _detect_currency(text)

        facts.extend(
            self._extract_monetary(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
                detected_currency=detected_currency,
            )
        )

        if "line_items_raw" in requested:
            fact = self._extract_line_items_raw(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
            )
            if fact is not None:
                facts.append(fact)

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
        detected_currency: str | None,
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

            inline_currency = _detect_currency(match.group(0))
            resolved_currency = inline_currency or detected_currency

            span_ids = _span_ids_for(spans, raw, fact_type)

            meta: dict[str, Any] = {
                "source": "ocr_label",
                "sanity_passed": sane,
            }
            if resolved_currency is not None:
                meta["currency"] = resolved_currency

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
                    metadata=meta,
                )
            )

        return facts

    def _extract_line_items_raw(
        self,
        text: str,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        spans: tuple[ExtractableSpan, ...],
    ) -> CandidateFact | None:
        lines = text.splitlines()
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if start_idx is None:
                for pattern in _LINE_ITEMS_START:
                    if pattern.search(line):
                        start_idx = i + 1
                        break
            elif end_idx is None:
                for pattern in _LINE_ITEMS_END:
                    if pattern.search(line):
                        end_idx = i
                        break

        if start_idx is None:
            return None

        if end_idx is None or end_idx <= start_idx:
            end_idx = len(lines)

        raw_block = "\n".join(
            ln for ln in lines[start_idx:end_idx] if ln.strip()
        ).strip()

        if not raw_block:
            return None

        span_ids = _span_ids_for(spans, lines[start_idx].strip(), "line_items_raw")

        return self._make_candidate_fact(
            document_id=document_id,
            source_id=source_id,
            entity_id=entity_id,
            fact_type="line_items_raw",
            source_stage=_SOURCE_STAGE,
            raw_value=raw_block,
            normalized_value=raw_block,
            confidence=_CONF_MEDIUM,
            span_ids=span_ids,
            metadata={
                "source": "block_extraction",
                "line_count": raw_block.count("\n") + 1,
            },
        )

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

                elif fact_type == "vat_rate":
                    normalized = _vat_rate_normalize(raw)
                    confidence = _CONF_HIGH

                elif fact_type == "currency":
                    normalized = _currency_normalize(raw)
                    confidence = _CONF_HIGH

                elif fact_type == "seller_vat_id":
                    normalized = _vat_id_normalize(raw)
                    valid = bool(re.match(r"^[A-Z]{2}\d{9,12}$", normalized))
                    extra_meta["format_valid"] = valid
                    confidence = _CONF_HIGH if valid else _CONF_MEDIUM

                elif fact_type == "seller_tax_id":
                    normalized = _tax_id_normalize(raw)
                    confidence = _CONF_HIGH

                elif fact_type == "invoice_number":
                    normalized = raw.strip()
                    confidence = _CONF_HIGH

                elif fact_type == "payment_reference":
                    normalized = self._normalize_whitespace(raw)
                    confidence = _CONF_HIGH

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
