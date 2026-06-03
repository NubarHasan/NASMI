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
from processing.extraction.extractors.base.mrz_parser import (
    MrzField,
    MrzParseResult,
    MRZType,
)
from processing.extraction.spatial_data import ExtractableSpan

_log = logging.getLogger(__name__)

_EXTRACTOR_ID: ExtractorId = ExtractorId("de.residence_permit.v1")
_SOURCE_STAGE: str = "extraction:residence_permit"
_SUPPORTED: frozenset[str] = frozenset(
    {
        "aufenthaltstitel",
        "residence_permit",
        "niederlassungserlaubnis",
        "aufenthaltserlaubnis",
    }
)

_ALL_FACT_TYPES: frozenset[str] = frozenset(
    {
        "document_code",
        "issuing_country",
        "surname",
        "given_names",
        "permit_number",
        "nationality",
        "date_of_birth",
        "sex",
        "date_of_expiry",
        "mrz_optional_identifier",
        "place_of_birth",
        "date_of_issue",
        "issuing_authority",
        "permit_type",
        "residence_address",
        "mrz_confidence",
        "mrz_status",
        "mrz_check_passed",
    }
)

_SEX_MAP: dict[str, str] = {
    "M": "male",
    "F": "female",
    "X": "unspecified",
    "<": "unspecified",
}

_PERMIT_TYPE_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"niederlassungserlaubnis", re.IGNORECASE), "permanent_residence"),
    (
        re.compile(r"erlaubnis\s+zum\s+daueraufenthalt", re.IGNORECASE),
        "permanent_residence",
    ),
    (re.compile(r"aufenthaltserlaubnis", re.IGNORECASE), "temporary_residence"),
    (re.compile(r"blaue?\s+karte\s+eu", re.IGNORECASE), "eu_blue_card"),
    (re.compile(r"blue\s+card", re.IGNORECASE), "eu_blue_card"),
    (re.compile(r"aufenthaltsgestattung", re.IGNORECASE), "asylum_seeker"),
    (re.compile(r"duldung", re.IGNORECASE), "tolerated_stay"),
    (re.compile(r"visum", re.IGNORECASE), "visa"),
]

_OCR_LABEL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "place_of_birth": [
        re.compile(
            r"(?:geburtsort|place\s+of\s+birth)[:\s]+([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß\s\-]+)",
            re.IGNORECASE,
        ),
    ],
    "date_of_issue": [
        re.compile(
            r"(?:ausstellungsdatum|date\s+of\s+issue)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
            re.IGNORECASE,
        ),
    ],
    "issuing_authority": [
        re.compile(
            r"(?:ausstellende\s+behörde|ausstellungsbehörde|issuing\s+authority)[:\s]+([^\n]+)",
            re.IGNORECASE,
        ),
    ],
    "permit_type": [
        re.compile(
            r"(?:aufenthaltstitel|art\s+des\s+aufenthaltstitels|permit\s+type)[:\s]+([^\n]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(niederlassungserlaubnis|aufenthaltserlaubnis|blaue?\s+karte\s+eu"
            r"|aufenthaltsgestattung|duldung)",
            re.IGNORECASE,
        ),
    ],
    "residence_address": [
        re.compile(
            r"(?:anschrift|adresse|wohnort|address)[:\s]+([^\n]+)",
            re.IGNORECASE,
        ),
    ],
}

_CONF_MRZ_BASE: float = 0.95
_CONF_MRZ_CHECK_FAIL: float = 0.60
_CONF_OCR_LABEL: float = 0.80


def _permit_type_normalize(raw: str) -> str:
    for pattern, normalized in _PERMIT_TYPE_MAP:
        if pattern.search(raw):
            return normalized
    return raw.strip().lower().replace(" ", "_")


def _span_ids_for(
    spans: tuple[ExtractableSpan, ...],
    query: str,
) -> tuple[SpanId, ...]:
    matched = tuple(s.span_id for s in spans if query.upper() in s.text.upper())
    return matched if matched else (spans[0].span_id,) if spans else ()


class ResidencePermitExtractor(GermanDocumentExtractor):

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

        mrz = self._parse_mrz(text)

        if mrz.mrz_type != MRZType.UNKNOWN:
            facts.extend(
                self._extract_from_mrz(
                    mrz,
                    document_id=document_id,
                    source_id=source_id,
                    entity_id=entity_id,
                    spans=spans,
                    requested=requested,
                )
            )
        else:
            _log.warning(
                "residence permit extractor: no MRZ found in document %r — falling back to OCR only",
                document_id,
            )

        facts.extend(
            self._extract_from_ocr(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
                already_extracted={f.fact_type for f in facts},
            )
        )

        return tuple(facts)

    def _extract_from_mrz(
        self,
        mrz: MrzParseResult,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        spans: tuple[ExtractableSpan, ...],
        requested: set[str],
    ) -> list[CandidateFact]:
        facts: list[CandidateFact] = []

        anchor = (mrz.normalized_lines[0] if mrz.normalized_lines else "")[:9]
        mrz_span_ids = _span_ids_for(spans, anchor)
        if not mrz_span_ids:
            _log.warning(
                "residence permit extractor: no spans matched MRZ anchor %r — facts will have no span",
                anchor,
            )

        check_ok = mrz.overall_check_success
        base_conf = _CONF_MRZ_BASE if check_ok else _CONF_MRZ_CHECK_FAIL

        mrz_meta: dict[str, Any] = {
            "mrz_type": mrz.mrz_type.value,
            "mrz_status": mrz.status.value,
            "mrz_confidence": mrz.confidence,
            "mrz_check_passed": check_ok,
        }

        def _fact(
            fact_type: str,
            raw: str,
            normalized: str,
            confidence: float,
            extra: dict[str, Any] | None = None,
        ) -> CandidateFact:
            return self._make_candidate_fact(
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                fact_type=fact_type,
                source_stage=_SOURCE_STAGE,
                raw_value=raw,
                normalized_value=normalized,
                confidence=confidence,
                span_ids=mrz_span_ids,
                metadata={"source": "mrz", **(extra or {}), **mrz_meta},
            )

        def _check_conf(field: MrzField) -> float:
            chk = next((c for c in mrz.check_results if c.field_name == field), None)
            return _CONF_MRZ_BASE if (chk and chk.is_valid) else _CONF_MRZ_CHECK_FAIL

        def _check_valid(field: MrzField) -> bool:
            chk = next((c for c in mrz.check_results if c.field_name == field), None)
            return chk.is_valid if chk else False

        if "document_code" in requested:
            val = mrz.clean(MrzField.DOCUMENT_CODE)
            if val:
                facts.append(_fact("document_code", val, val, base_conf))

        if "issuing_country" in requested:
            val = mrz.clean(MrzField.ISSUING_COUNTRY)
            if val:
                facts.append(_fact("issuing_country", val, val, base_conf))

        if "surname" in requested:
            val = mrz.clean(MrzField.SURNAME)
            raw = mrz.field(MrzField.SURNAME) or ""
            if val:
                facts.append(_fact("surname", raw, val, base_conf))

        if "given_names" in requested:
            val = mrz.clean(MrzField.GIVEN_NAMES)
            raw = mrz.field(MrzField.GIVEN_NAMES) or ""
            if val:
                facts.append(_fact("given_names", raw, val, base_conf))

        if "permit_number" in requested:
            val = mrz.clean(MrzField.DOCUMENT_NUMBER)
            raw = mrz.field(MrzField.DOCUMENT_NUMBER) or ""
            if val:
                facts.append(
                    _fact(
                        "permit_number",
                        raw,
                        val,
                        _check_conf(MrzField.DOCUMENT_NUMBER),
                        {"check_digit_valid": _check_valid(MrzField.DOCUMENT_NUMBER)},
                    )
                )

        if "nationality" in requested:
            val = mrz.clean(MrzField.NATIONALITY)
            raw = mrz.field(MrzField.NATIONALITY) or ""
            if val:
                facts.append(_fact("nationality", raw, val, base_conf))

        if "date_of_birth" in requested:
            raw = mrz.field(MrzField.DATE_OF_BIRTH) or ""
            if raw:
                result = self._validate_birth_date(raw)
                normalized = (
                    result.value.isoformat() if result.value is not None else raw
                )
                facts.append(
                    _fact(
                        "date_of_birth",
                        raw,
                        normalized,
                        _check_conf(MrzField.DATE_OF_BIRTH),
                        {
                            "check_digit_valid": _check_valid(MrzField.DATE_OF_BIRTH),
                            "date_valid": result.value is not None,
                        },
                    )
                )

        if "sex" in requested:
            raw = mrz.field(MrzField.SEX) or ""
            norm = _SEX_MAP.get(raw, "unspecified")
            facts.append(_fact("sex", raw, norm, base_conf))

        if "date_of_expiry" in requested:
            raw = mrz.field(MrzField.EXPIRY_DATE) or ""
            if raw:
                result = self._validate_expiry_date(raw)
                normalized = (
                    result.value.isoformat() if result.value is not None else raw
                )
                facts.append(
                    _fact(
                        "date_of_expiry",
                        raw,
                        normalized,
                        _check_conf(MrzField.EXPIRY_DATE),
                        {
                            "check_digit_valid": _check_valid(MrzField.EXPIRY_DATE),
                            "date_valid": result.value is not None,
                        },
                    )
                )

        if "mrz_optional_identifier" in requested:
            val = mrz.clean(MrzField.PERSONAL_NUMBER)
            raw = mrz.field(MrzField.PERSONAL_NUMBER) or ""
            if val:
                facts.append(
                    _fact(
                        "mrz_optional_identifier",
                        raw,
                        val,
                        _check_conf(MrzField.PERSONAL_NUMBER),
                        {
                            "check_digit_valid": _check_valid(MrzField.PERSONAL_NUMBER),
                            "source_mrz_field": "PERSONAL_NUMBER",
                        },
                    )
                )

        if "mrz_confidence" in requested:
            v = str(mrz.confidence)
            facts.append(_fact("mrz_confidence", v, v, 1.0))

        if "mrz_status" in requested:
            v = mrz.status.value
            facts.append(_fact("mrz_status", v, v, 1.0))

        if "mrz_check_passed" in requested:
            v = str(check_ok)
            facts.append(_fact("mrz_check_passed", v, v, 1.0))

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

                try:
                    raw = match.group(1).strip()
                except IndexError:
                    raw = match.group(0).strip()

                if not raw:
                    continue

                if fact_type == "date_of_issue":
                    result = try_parse_date(raw)
                    normalized = (
                        result.value.isoformat() if result.value is not None else raw
                    )
                elif fact_type == "permit_type":
                    normalized = _permit_type_normalize(raw)
                else:
                    normalized = self._normalize_whitespace(raw)

                span_ids = _span_ids_for(spans, raw)
                if not span_ids:
                    _log.debug(
                        "residence permit extractor: no span matched OCR value %r for %r",
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
                        confidence=_CONF_OCR_LABEL,
                        span_ids=span_ids,
                        metadata={"source": "ocr_label"},
                    )
                )
                break

        return facts
