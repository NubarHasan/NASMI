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

_EXTRACTOR_ID: ExtractorId = ExtractorId("de.bank_statement.v1")
_SOURCE_STAGE: str = "extraction:bank_statement"
_SUPPORTED: frozenset[str] = frozenset(
    {
        "bank_statement",
        "kontoauszug",
        "kontoübersicht",
    }
)

_ALL_FACT_TYPES: frozenset[str] = frozenset(
    {
        "account_holder_name",
        "iban",
        "bic",
        "bank_name",
        "statement_period_start",
        "statement_period_end",
        "opening_balance",
        "closing_balance",
        "total_credits",
        "total_debits",
        "currency",
    }
)

_CONF_HIGH: float = 0.90
_CONF_MEDIUM: float = 0.75
_CONF_LOW: float = 0.55

_DATE_FACT_TYPES: frozenset[str] = frozenset(
    {
        "statement_period_start",
        "statement_period_end",
    }
)

_MONETARY_FACT_TYPES: frozenset[str] = frozenset(
    {
        "opening_balance",
        "closing_balance",
        "total_credits",
        "total_debits",
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

_IBAN_RE: re.Pattern[str] = re.compile(
    r"\b([A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){4,7})\b",
    re.IGNORECASE,
)

_BIC_RE: re.Pattern[str] = re.compile(
    r"\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b",
)

_HUMAN_NAME_RE: re.Pattern[str] = re.compile(
    r"^[A-ZÄÖÜ][a-zäöüß]+(?:[\s\-][A-ZÄÖÜ][a-zäöüß]+)+$",
)


def _amount_normalize(raw: str) -> str:
    cleaned = raw.strip().replace("\xa0", "").replace(" ", "")
    if re.search(r"\d\.\d{3},", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.search(r"\d,\d{3}\.", cleaned):
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    cleaned = cleaned.lstrip("+-").strip()
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return raw.strip()


def _balance_sign(raw: str) -> str | None:
    s = raw.strip()
    if s.startswith("-") or s.endswith("-") or re.search(r"\bS\b", s):
        return "debit"
    if s.startswith("+") or s.endswith("+") or re.search(r"\bH\b", s):
        return "credit"
    return None


def _iban_normalize(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def _iban_format_valid(normalized: str) -> bool:
    return bool(re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$", normalized))


def _iban_checksum_valid(normalized: str) -> bool:
    if len(normalized) < 5:
        return False
    rearranged = normalized[4:] + normalized[:4]
    digits = ""
    for ch in rearranged:
        if ch.isdigit():
            digits += ch
        elif ch.isalpha():
            digits += str(ord(ch.upper()) - ord("A") + 10)
        else:
            return False
    try:
        return int(digits) % 97 == 1
    except ValueError:
        return False


def _bic_normalize(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def _bic_valid(normalized: str) -> bool:
    return bool(re.match(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$", normalized))


def _currency_normalize(raw: str) -> str:
    return _CURRENCY_MAP.get(raw.strip().lower(), raw.strip().upper())


def _detect_currency(text: str) -> str | None:
    match = _INLINE_CURRENCY_RE.search(text)
    if match:
        return _currency_normalize(match.group(1))
    return None


def _looks_like_human_name(value: str) -> bool:
    return bool(_HUMAN_NAME_RE.match(value.strip()))


_MONETARY_BOUNDS: dict[str, tuple[float, float]] = {
    "opening_balance": (-10_000_000.0, 10_000_000.0),
    "closing_balance": (-10_000_000.0, 10_000_000.0),
    "total_credits": (0.0, 10_000_000.0),
    "total_debits": (0.0, 10_000_000.0),
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
        "opening_balance",
        re.compile(
            r"(?:anfangssaldo|eröffnungssaldo|saldo\s+(?:zu\s+beginn|vortrag|alt)|"
            r"opening\s+balance|alter\s+saldo)"
            r"[:\s]+([-+]?[\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
    (
        "closing_balance",
        re.compile(
            r"(?:schlusssaldo|endsaldo|neuer\s+saldo|saldo\s+(?:zum\s+ende|neu)|"
            r"closing\s+balance|kontostand)"
            r"[:\s]+([-+]?[\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
    (
        "total_credits",
        re.compile(
            r"(?:gutschriften\s+gesamt|gesamte?\s+gutschriften|"
            r"summe\s+(?:der\s+)?gutschriften|total\s+credits|eingänge\s+gesamt)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
    (
        "total_debits",
        re.compile(
            r"(?:belastungen\s+gesamt|gesamte?\s+belastungen|"
            r"summe\s+(?:der\s+)?belastungen|total\s+debits|ausgänge\s+gesamt)"
            r"[:\s]+([\d.,\s]+)\s*(?:€|EUR|euro|CHF|USD|\$|£|GBP)?",
            re.IGNORECASE,
        ),
    ),
]

_OCR_LABEL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "account_holder_name": [
        re.compile(
            r"(?:kontoinhaber(?:in)?|konto\s+lautend\s+auf|account\s+holder|"
            r"name\s+des\s+kontoinhabers)"
            r"[:\s]+([^\n,]{2,80})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:herr(?:n)?|frau)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+)"
            r"(?=\s*\n\s*(?:[A-ZÄÖÜ]|\d{5}))",
            re.IGNORECASE,
        ),
    ],
    "iban": [
        re.compile(
            r"(?:iban)[:\s]+([A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){4,7})",
            re.IGNORECASE,
        ),
        _IBAN_RE,
    ],
    "bic": [
        re.compile(
            r"(?:bic|swift(?:-?code)?)[:\s]+([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)",
            re.IGNORECASE,
        ),
        _BIC_RE,
    ],
    "bank_name": [
        re.compile(
            r"(?:bank(?:name)?|kreditinstitut|institute)[:\s]+([^\n,]{2,80})",
            re.IGNORECASE,
        ),
        re.compile(
            r"^((?:Deutsche\s+Bank|Commerzbank|Sparkasse|Volksbank|"
            r"Raiffeisenbank|DKB|ING|Postbank|HypoVereinsbank|"
            r"Landesbank|Stadtsparkasse|Kreissparkasse)[^\n]{0,60})$",
            re.IGNORECASE | re.MULTILINE,
        ),
    ],
    "statement_period_start": [
        re.compile(
            r"(?:kontoauszug(?:\s+für)?|abrechnungszeitraum|"
            r"zeitraum|statement\s+period|period)"
            r"[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})"
            r"(?=\s*(?:bis|to|–|-)\s*\d)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:von|from)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})"
            r"(?=\s*(?:bis|to|–|-)\s*\d)",
            re.IGNORECASE,
        ),
    ],
    "statement_period_end": [
        re.compile(
            r"(?:abrechnungszeitraum|zeitraum|statement\s+period|period)"
            r"[:\s]+\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}"
            r"\s*(?:bis|to|–|-)\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:bis|to)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "currency": [
        re.compile(
            r"(?:währung|currency)[:\s]+(€|EUR|euro|CHF|USD|\$|£|GBP)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:saldo|kontostand|balance)" r"[^\n]{0,40}(€|EUR|euro|CHF|USD|\$|£|GBP)",
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
        "bank_statement extractor: no span matched %r for %r — fact retained with empty span_ids",
        query,
        context,
    )
    return ()


class BankStatementExtractor(GermanDocumentExtractor):

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

            sign = _balance_sign(raw)
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
            if sign is not None:
                meta["sign"] = sign

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

                elif fact_type == "iban":
                    normalized = _iban_normalize(raw)
                    fmt_valid = _iban_format_valid(normalized)
                    chk_valid = _iban_checksum_valid(normalized) if fmt_valid else False
                    extra_meta["format_valid"] = fmt_valid
                    extra_meta["checksum_valid"] = chk_valid
                    confidence = (
                        _CONF_HIGH
                        if fmt_valid and chk_valid
                        else _CONF_MEDIUM if fmt_valid else _CONF_LOW
                    )

                elif fact_type == "bic":
                    normalized = _bic_normalize(raw)
                    valid = _bic_valid(normalized)
                    extra_meta["format_valid"] = valid
                    confidence = _CONF_HIGH if valid else _CONF_LOW

                elif fact_type == "currency":
                    normalized = _currency_normalize(raw)
                    confidence = _CONF_HIGH

                elif fact_type == "account_holder_name":
                    normalized = self._normalize_whitespace(raw)
                    is_human = _looks_like_human_name(normalized)
                    extra_meta["looks_like_name"] = is_human
                    confidence = _CONF_MEDIUM if is_human else _CONF_LOW

                elif fact_type == "bank_name":
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
