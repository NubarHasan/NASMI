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

_EXTRACTOR_ID: ExtractorId = ExtractorId("de.passport.v2")
_SOURCE_STAGE: str = "extraction:passport"
_SUPPORTED: frozenset[str] = frozenset({"reisepass", "passport"})

_ALL_FACT_TYPES: frozenset[str] = frozenset(
    {
        "document_code",
        "issuing_country",
        "surname",
        "given_names",
        "passport_number",
        "nationality",
        "date_of_birth",
        "sex",
        "date_of_expiry",
        "personal_number",
        "place_of_birth",
        "date_of_issue",
        "issuing_authority",
        "mrz_confidence",
        "mrz_status",
        "mrz_check_passed",
        "document_keyword",
        "possible_location",
        "possible_date",
        "document_label",
        "review_candidate",
    }
)

_SEX_MAP: dict[str, str] = {
    "M": "male",
    "F": "female",
    "X": "unspecified",
    "<": "unspecified",
}

_LABEL_DEFINITIONS: dict[str, list[str]] = {
    "surname": [
        "surname",
        "name",
        "familienname",
        "nom",
    ],
    "given_names": [
        "given names",
        "given name",
        "vornamen",
        "vorname",
        "prénoms",
        "prenoms",
    ],
    "place_of_birth": [
        "geburtsort",
        "place of birth",
        "lieu de naissance",
    ],
    "date_of_birth": [
        "geburtsdatum",
        "date of birth",
        "date de naissance",
    ],
    "date_of_issue": [
        "ausstellungsdatum",
        "date of issue",
        "date de délivrance",
        "date de delivrance",
    ],
    "date_of_expiry": [
        "gültig bis",
        "gueltig bis",
        "date of expiry",
        "expiry date",
        "date d'expiration",
    ],
    "issuing_authority": [
        "ausstellende behörde",
        "ausstellungsbehörde",
        "issuing authority",
        "autorité",
        "autorite",
    ],
    "passport_number": [
        "passnummer",
        "passport no",
        "passport number",
        "document no",
    ],
    "nationality": [
        "staatsangehörigkeit",
        "staatsangehoerigkeit",
        "nationality",
        "nationalité",
        "nationalite",
    ],
    "religious_name_or_pseudonym": [
        "ordens- oder künstlername",
        "ordens- oder kuenstlername",
        "religious name or pseudonym",
        "nom de religion ou pseudonyme",
        "or pseudonym",
    ],
    "residence": [
        "wohnort",
        "residence",
        "domicile",
    ],
    "height": [
        "größe",
        "groesse",
        "height",
        "taille",
    ],
    "eye_color": [
        "augenfarbe",
        "colour of eyes",
        "color of eyes",
        "couleur des yeux",
    ],
}

_LABEL_VALUE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "place_of_birth": [
        re.compile(
            r"(?:geburtsort|place\s+of\s+birth)[:\s]+([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß\s\-]{2,40})",
            re.IGNORECASE,
        ),
    ],
    "date_of_issue": [
        re.compile(
            r"(?:ausstellungsdatum|date\s+of\s+issue)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
            re.IGNORECASE,
        ),
    ],
    "issuing_authority": [
        re.compile(
            r"(?:ausstellende\s+behörde|ausstellungsbehörde|issuing\s+authority)[:\s]+([^\n]{3,80})",
            re.IGNORECASE,
        ),
    ],
    "passport_number": [
        re.compile(
            r"(?:passnummer|passport\s+no\.?|passport\s+number|document\s+no\.?)[:\s]+([A-Z0-9]{6,12})",
            re.IGNORECASE,
        ),
    ],
    "surname": [
        re.compile(
            r"(?:surname|familienname)[:\s]+([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß\s\-]{2,40})",
            re.IGNORECASE,
        ),
    ],
    "given_names": [
        re.compile(
            r"(?:given\s+names?|vorname[n]?)[:\s]+([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß\s\-]{2,50})",
            re.IGNORECASE,
        ),
    ],
    "nationality": [
        re.compile(
            r"(?:nationality|staatsangehörigkeit|staatsangehoerigkeit)[:\s]+([A-ZÄÖÜa-zäöüß\s\-]{2,40})",
            re.IGNORECASE,
        ),
    ],
}

_FALLBACK_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "document_keyword": [
        re.compile(r"\b(REISEPASS|PASSPORT)\b", re.IGNORECASE),
        re.compile(
            r"\b(BUNDESREPUBLIK\s+DEUTSCHLAND|FEDERAL\s+REPUBLIC\s+OF\s+GERMANY)\b",
            re.IGNORECASE,
        ),
    ],
    "issuing_country": [
        re.compile(r"\b(DEU|D|DEUTSCHLAND|GERMANY)\b", re.IGNORECASE),
    ],
    "possible_location": [
        re.compile(
            r"\b(EISENACH|BERLIN|HAMBURG|MÜNCHEN|MUNICH|KÖLN|KOELN|FRANKFURT|STUTTGART|DÜSSELDORF|DUSSELDORF)\b",
            re.IGNORECASE,
        ),
    ],
    "possible_date": [
        re.compile(r"\b(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\b"),
    ],
    "passport_number": [
        re.compile(r"\b([CFGHJKLMNPRTVWXYZ0-9]{8,10})\b", re.IGNORECASE),
    ],
}

_BAD_VALUE_FRAGMENTS: tuple[str, ...] = (
    "or pseudonym",
    "religious name",
    "nom de religion",
    "residence",
    "domicile",
    "height",
    "taille",
    "colour of eyes",
    "color of eyes",
    "couleur des yeux",
    "surname",
    "given name",
    "given names",
    "place of birth",
    "date of birth",
    "date of issue",
    "issuing authority",
    "nationality",
    "passport number",
    "passport no",
    "document no",
)

_CONF_MRZ_BASE: float = 0.95
_CONF_MRZ_CHECK_FAIL: float = 0.60
_CONF_OCR_LABEL: float = 0.76
_CONF_OCR_SUSPICIOUS: float = 0.32
_CONF_OCR_FALLBACK: float = 0.45
_CONF_LABEL: float = 0.88


def _span_ids_for(
    spans: tuple[ExtractableSpan, ...],
    query: str,
    document_id: DocumentId | None = None,
) -> tuple[SpanId, ...]:
    matched = tuple(
        s.span_id for s in spans if query and query.upper() in s.text.upper()
    )
    if matched:
        return matched

    if spans:
        return (spans[0].span_id,)

    if document_id is not None:
        clean_id = str(document_id).replace("DOC-", "")
        return (SpanId(f"SPAN-{clean_id[:24]}"),)

    return (SpanId("SPAN-000000000000000000000000"),)


class PassportExtractor(GermanDocumentExtractor):

    @property
    def extractor_id(self) -> ExtractorId:
        return _EXTRACTOR_ID

    @property
    def supported_document_types(self) -> frozenset[str]:
        return _SUPPORTED

    def _extract(self, request: ExtractionRequest) -> tuple[CandidateFact, ...]:
        content = request.content
        text = self._text(request)
        text = self._normalize_ocr_noise(text)
        spans = self._spans(request)
        document_id = content.document_id
        source_id = content.source_id
        entity_id = request.entity_id
        requested = set(request.requested_fact_types) or set(_ALL_FACT_TYPES)
        facts: list[CandidateFact] = []

        facts.extend(
            self._extract_labels(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
            )
        )

        mrz = self._parse_mrz(text)

        if mrz.mrz_type == MRZType.UNKNOWN:
            fuzzy_text = self._build_fuzzy_mrz_text(text)
            if fuzzy_text != text:
                mrz = self._parse_mrz(fuzzy_text)

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
                "passport extractor: no MRZ found in document %r — falling back to OCR only",
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
                already_extracted={
                    f.fact_type for f in facts if f.fact_type != "document_label"
                },
            )
        )

        facts.extend(
            self._extract_fallback(
                text,
                document_id=document_id,
                source_id=source_id,
                entity_id=entity_id,
                spans=spans,
                requested=requested,
                already_extracted={
                    f.fact_type
                    for f in facts
                    if f.fact_type not in {"document_label", "review_candidate"}
                },
            )
        )

        return tuple(facts)

    def _extract_labels(
        self,
        text: str,
        *,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        spans: tuple[ExtractableSpan, ...],
        requested: set[str],
    ) -> list[CandidateFact]:
        if "document_label" not in requested:
            return []

        facts: list[CandidateFact] = []
        lowered = text.lower()
        seen: set[str] = set()

        for normalized_label, variants in _LABEL_DEFINITIONS.items():
            for label in variants:
                if label.lower() not in lowered:
                    continue

                key = f"{normalized_label}:{label.lower()}"
                if key in seen:
                    continue

                seen.add(key)
                span_ids = _span_ids_for(spans, label, document_id)

                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type="document_label",
                        source_stage=_SOURCE_STAGE,
                        raw_value=label,
                        normalized_value=normalized_label,
                        confidence=_CONF_LABEL,
                        span_ids=span_ids,
                        metadata={
                            "source": "ocr_label_catalog",
                            "role": "document_label",
                            "label_text": label,
                            "normalized_label": normalized_label,
                            "is_person_fact": False,
                            "store_as_knowledge_evidence": True,
                        },
                    )
                )
                break

        return facts

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
        mrz_span_ids = _span_ids_for(spans, anchor, document_id)

        check_ok = mrz.overall_check_success
        base_conf = _CONF_MRZ_BASE if check_ok else _CONF_MRZ_CHECK_FAIL

        mrz_meta: dict[str, Any] = {
            "source": "mrz",
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
                metadata={**mrz_meta, **(extra or {})},
            )

        def _check_conf(field: MrzField) -> float:
            chk = next((c for c in mrz.check_results if c.field_name == field), None)
            return _CONF_MRZ_BASE if (chk and chk.is_valid) else _CONF_MRZ_CHECK_FAIL

        def _check_valid(field: MrzField) -> bool:
            chk = next((c for c in mrz.check_results if c.field_name == field), None)
            return chk.is_valid if chk else False

        field_map = [
            ("document_code", MrzField.DOCUMENT_CODE),
            ("issuing_country", MrzField.ISSUING_COUNTRY),
            ("surname", MrzField.SURNAME),
            ("given_names", MrzField.GIVEN_NAMES),
            ("nationality", MrzField.NATIONALITY),
            ("personal_number", MrzField.PERSONAL_NUMBER),
        ]

        for fact_type, field in field_map:
            if fact_type not in requested:
                continue

            val = mrz.clean(field)
            if not val:
                continue

            if self._looks_like_label_value(val):
                continue

            raw_field = mrz.field(field)
            raw = raw_field if raw_field is not None else val

            facts.append(_fact(fact_type, raw, val, base_conf))

        if "passport_number" in requested:
            val = mrz.clean(MrzField.DOCUMENT_NUMBER)
            raw = mrz.field(MrzField.DOCUMENT_NUMBER) or ""
            if val:
                facts.append(
                    _fact(
                        "passport_number",
                        raw,
                        val,
                        _check_conf(MrzField.DOCUMENT_NUMBER),
                        {"check_digit_valid": _check_valid(MrzField.DOCUMENT_NUMBER)},
                    )
                )

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
            if raw:
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

        for fact_type, patterns in _LABEL_VALUE_PATTERNS.items():
            if fact_type not in targets:
                continue

            for pattern in patterns:
                match = pattern.search(text)
                if not match:
                    continue

                raw = self._clean_candidate_value(match.group(1))
                if not raw:
                    continue

                suspicious = self._looks_like_label_value(raw)

                if fact_type == "date_of_issue":
                    result = try_parse_date(raw)
                    normalized = (
                        result.value.isoformat() if result.value is not None else raw
                    )
                else:
                    normalized = self._normalize_whitespace(raw)

                span_ids = _span_ids_for(spans, raw, document_id)

                if suspicious:
                    if "review_candidate" in requested:
                        facts.append(
                            self._make_candidate_fact(
                                document_id=document_id,
                                source_id=source_id,
                                entity_id=entity_id,
                                fact_type="review_candidate",
                                source_stage=_SOURCE_STAGE,
                                raw_value=raw,
                                normalized_value=fact_type,
                                confidence=_CONF_OCR_SUSPICIOUS,
                                span_ids=span_ids,
                                metadata={
                                    "source": "ocr_label_value",
                                    "target_field": fact_type,
                                    "candidate_value": raw,
                                    "review_reason": "candidate value looks like a document label, not a real personal value",
                                    "is_person_fact": False,
                                },
                            )
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
                        metadata={
                            "source": "ocr_label_value",
                            "is_person_fact": True,
                        },
                    )
                )
                break

        return facts

    def _extract_fallback(
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
        targets = requested - already_extracted

        for fact_type, patterns in _FALLBACK_PATTERNS.items():
            if fact_type not in targets:
                continue

            for pattern in patterns:
                match = pattern.search(text)
                if not match:
                    continue

                raw = self._clean_candidate_value(match.group(1))
                if not raw or self._looks_like_label_value(raw):
                    continue

                normalized = self._normalize_whitespace(raw)

                if fact_type == "possible_date":
                    parsed = try_parse_date(raw)
                    if parsed.value is not None:
                        normalized = parsed.value.isoformat()

                span_ids = _span_ids_for(spans, raw, document_id)

                facts.append(
                    self._make_candidate_fact(
                        document_id=document_id,
                        source_id=source_id,
                        entity_id=entity_id,
                        fact_type=fact_type,
                        source_stage=_SOURCE_STAGE,
                        raw_value=raw,
                        normalized_value=normalized,
                        confidence=_CONF_OCR_FALLBACK,
                        span_ids=span_ids,
                        metadata={
                            "source": "ocr_fallback",
                            "is_person_fact": fact_type not in {"document_keyword"},
                        },
                    )
                )
                break

        return facts

    def _looks_like_label_value(self, value: str) -> bool:
        v = self._normalize_whitespace(value).lower().strip(" :;.,-/")
        if len(v) < 2:
            return True

        for bad in _BAD_VALUE_FRAGMENTS:
            if bad in v:
                return True

        label_hits = 0
        for variants in _LABEL_DEFINITIONS.values():
            for label in variants:
                if label.lower() in v:
                    label_hits += 1

        if label_hits > 0:
            return True

        words = [w for w in re.split(r"\s+", v) if w]
        return bool(len(words) > 5 and not any(ch.isdigit() for ch in v))

    def _clean_candidate_value(self, value: str) -> str:
        value = self._normalize_whitespace(value)
        value = re.sub(r"^[/:;,\.\-\s]+", "", value)
        value = re.sub(r"[/:;,\.\-\s]+$", "", value)
        value = re.sub(r"\s{2,}", " ", value)
        return value.strip()

    def _normalize_ocr_noise(self, text: str) -> str:
        replacements = {
            "‘": "",
            "’": "",
            "“": "",
            "”": "",
            "|": "I",
            "«": "<",
            "»": "<",
            "‹": "<",
            "›": "<",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _build_fuzzy_mrz_text(self, text: str) -> str:
        lines = [self._normalize_whitespace(line).upper() for line in text.splitlines()]
        candidates: list[str] = []

        for line in lines:
            compact = re.sub(r"[^A-Z0-9<]", "", line)
            compact = compact.replace(" ", "")
            compact = (
                compact.replace("O", "0")
                if any(ch.isdigit() for ch in compact)
                else compact
            )

            if "<<" in compact or compact.count("<") >= 4:
                candidates.append(compact)
                continue

            if re.search(r"[A-Z0-9]{8,12}<<\d{6}", compact):
                candidates.append(compact)

        normalized_candidates: list[str] = []
        for candidate in candidates:
            if 30 <= len(candidate) <= 50:
                normalized_candidates.append(candidate[:44].ljust(44, "<"))

        if len(normalized_candidates) >= 2:
            return "\n".join(normalized_candidates[:2]) + "\n" + text

        if len(normalized_candidates) == 1:
            return normalized_candidates[0] + "\n" + text

        return text
