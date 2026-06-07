from __future__ import annotations

import re
from typing import Final

from core.identifiers import generate_span_id
from core.types import DocumentId, EntityId, ExtractorId, SourceId, SpanId
from processing.extraction.candidate_fact import CandidateFact
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.extraction.extractor import Extractor

_EXTRACTOR_ID: Final[ExtractorId] = ExtractorId("universal.document.v1")
_SOURCE_STAGE: Final[str] = "extraction:universal"

_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "surname": ("surname", "family name", "familienname", "name", "nom"),
    "given_names": ("given names", "given name", "vornamen", "vorname", "prenoms", "prénoms"),
    "passport_number": ("passport number", "passport no", "pass-nr", "pass nr", "passnummer", "document no", "document number", "passeport no"),
    "nationality": ("nationality", "staatsangehörigkeit", "staatsangehoerigkeit", "nationalité", "nationalite"),
    "date_of_birth": ("date of birth", "geburtsdatum", "date de naissance", "geb.", "geburt"),
    "place_of_birth": ("place of birth", "geburtsort", "lieu de naissance", "birth place"),
    "date_of_issue": ("date of issue", "ausstellungsdatum", "date de délivrance", "date de delivrance"),
    "date_of_expiry": ("date of expiry", "expiry date", "gültig bis", "gueltig bis", "date d'expiration", "valid until"),
    "issuing_authority": ("issuing authority", "ausstellende behörde", "ausstellungsbehörde", "autorité", "autorite"),
    "sex": ("sex", "geschlecht", "sexe"),
    "height": ("height", "größe", "groesse", "taille"),
    "eye_color": ("eye color", "colour of eyes", "augenfarbe", "couleur des yeux"),
    "address": ("address", "adresse", "anschrift", "wohnort", "residence", "domicile"),
    "iban": ("iban",),
    "bic": ("bic", "swift"),
    "tax_id": ("tax id", "steuer id", "steueridentifikationsnummer"),
    "employer": ("employer", "arbeitgeber"),
    "employee": ("employee", "arbeitnehmer"),
    "gross_salary": ("gross salary", "brutto", "bruttogehalt"),
    "net_salary": ("net salary", "netto", "nettogehalt"),
    "invoice_number": ("invoice number", "invoice no", "rechnungsnummer"),
    "customer_number": ("customer number", "kundennummer"),
}

_DATE_FIELDS: Final[set[str]] = {
    "date_of_birth",
    "date_of_issue",
    "date_of_expiry",
}

_TEXT_NAME_FIELDS: Final[set[str]] = {
    "surname",
    "given_names",
    "place_of_birth",
    "issuing_authority",
    "employer",
    "employee",
    "address",
}

_PATTERN_DEFINITIONS: tuple[tuple[str, re.Pattern[str], float], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE), 0.80),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b", re.IGNORECASE), 0.82),
    ("phone_number", re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)"), 0.55),
    ("date", re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"), 0.55),
    ("amount", re.compile(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\s?(?:EUR|€)\b", re.IGNORECASE), 0.45),
    ("document_number", re.compile(r"\b[A-Z]{1,3}\d{5,10}\b", re.IGNORECASE), 0.45),
)

_CONTEXTUAL_PATTERNS: dict[str, tuple[re.Pattern[str], float]] = {
    "bic": (re.compile(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", re.IGNORECASE), 0.65),
    "passport_number": (re.compile(r"\b[A-Z0-9]{8,10}\b", re.IGNORECASE), 0.55),
}

_BAD_LINE_PARTS: tuple[str, ...] = (
    "http://",
    "https://",
    "www.",
)

_NOISE_VALUES: frozenset[str] = frozenset(
    {
        "bundesrepublik deutschland",
        "federal republic of germany",
        "republique federale",
        "république fédérale",
        "republic",
        "federale",
        "passport",
        "passeport",
        "reisepass",
        "nationality",
        "nationalité",
        "nationalite",
        "surname",
        "name",
        "given names",
        "given name",
        "vornamen",
        "geburtsname",
        "date of birth",
        "geburt",
        "geburtsdatum",
        "sex",
        "gender",
        "height",
        "colour of eyes",
        "eye color",
        "eye colour",
        "residence",
        "wohnort",
        "domicile",
        "passport no",
        "passport number",
        "autorité",
        "autorite",
        "authority",
        "issuing authority",
        "inhabers",
        "gsnummer",
    }
)

_COUNTRY_WORDS: frozenset[str] = frozenset(
    {
        "deutschland",
        "germany",
        "allemagne",
        "syrien",
        "syria",
        "syrian",
        "deutsch",
        "german",
        "federal",
        "republic",
    }
)


class UniversalDocumentExtractor(Extractor):

    @property
    def extractor_id(self) -> ExtractorId:
        return _EXTRACTOR_ID

    @property
    def supported_document_types(self) -> frozenset[str]:
        return frozenset(
            {
                "universal",
                "unknown",
                "other",
                "document",
                "any",
                "passport",
                "id_card",
                "residence_permit",
                "invoice",
                "payslip",
                "bank_statement",
            }
        )

    def can_handle(self, request: ExtractionRequest) -> bool:
        return bool((request.content.normalized_text or request.content.raw_text or "").strip())

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        text = _normalize_text(request.content.normalized_text or request.content.raw_text or "")
        facts: list[CandidateFact] = []
        facts.extend(self._extract_label_values(request, text))
        facts.extend(self._extract_patterns(request, text))
        facts.extend(self._extract_contextual_patterns(request, text))
        facts.extend(self._extract_mrz(request, text))
        facts = _dedupe([fact for fact in facts if _candidate_is_safe(fact)])

        return ExtractionResult.success(
            document_id=request.content.document_id,
            source_id=request.content.source_id,
            extractor_id=self.extractor_id,
            candidate_facts=tuple(facts),
            metadata={
                "extractor": "universal",
                "strategy": "strict_quality_gate",
                "candidate_count": len(facts),
            },
        )

    def _extract_label_values(self, request: ExtractionRequest, text: str) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        lines = _clean_lines(text)

        for index, line in enumerate(lines):
            lower = _norm(line)

            for field, labels in _FIELD_LABELS.items():
                matched_label = next((label for label in labels if _label_matches(lower, label)), None)
                if matched_label is None:
                    continue

                value = _value_after_label(line, matched_label)

                if not value and index + 1 < len(lines) and _line_is_standalone_label(line, matched_label):
                    value = lines[index + 1]

                value = _clean_value(value)

                if not _is_valid_field_value(field, value):
                    continue

                facts.append(
                    _candidate(
                        request=request,
                        fact_type=field,
                        raw_value=value,
                        normalized_value=_normalize_field_value(field, value),
                        confidence=0.68,
                        line_index=index,
                        metadata={
                            "source": "universal_label_value",
                            "matched_label": matched_label,
                            "review_editable": True,
                            "auto_accept": False,
                            "is_person_fact": field not in {"iban", "bic", "gross_salary", "net_salary", "invoice_number", "customer_number"},
                            "needs_human_review": True,
                        },
                    )
                )

        return facts

    def _extract_patterns(self, request: ExtractionRequest, text: str) -> list[CandidateFact]:
        facts: list[CandidateFact] = []

        for fact_type, pattern, confidence in _PATTERN_DEFINITIONS:
            for match in pattern.finditer(text):
                value = _clean_value(match.group(0))
                if not _is_valid_pattern_value(fact_type, value):
                    continue

                facts.append(
                    _candidate(
                        request=request,
                        fact_type=fact_type,
                        raw_value=value,
                        normalized_value=_normalize_field_value(fact_type, value),
                        confidence=confidence,
                        line_index=_line_index_for_match(text, match.start()),
                        metadata={
                            "source": "universal_regex",
                            "review_editable": True,
                            "auto_accept": False,
                            "is_person_fact": fact_type not in {"amount"},
                            "needs_human_review": True,
                        },
                    )
                )

        return facts

    def _extract_contextual_patterns(self, request: ExtractionRequest, text: str) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        lines = _clean_lines(text)

        for index, line in enumerate(lines):
            lower = _norm(line)

            for fact_type, (pattern, confidence) in _CONTEXTUAL_PATTERNS.items():
                labels = _FIELD_LABELS.get(fact_type, ())
                if not any(_label_matches(lower, label) for label in labels):
                    continue

                for match in pattern.finditer(line):
                    value = _clean_value(match.group(0))
                    if not _is_valid_field_value(fact_type, value):
                        continue

                    facts.append(
                        _candidate(
                            request=request,
                            fact_type=fact_type,
                            raw_value=value,
                            normalized_value=_normalize_field_value(fact_type, value),
                            confidence=confidence,
                            line_index=index,
                            metadata={
                                "source": "universal_contextual_regex",
                                "review_editable": True,
                                "auto_accept": False,
                                "is_person_fact": True,
                                "needs_human_review": True,
                            },
                        )
                    )

        return facts

    def _extract_mrz(self, request: ExtractionRequest, text: str) -> list[CandidateFact]:
        facts: list[CandidateFact] = []
        lines = _clean_lines(text)

        for index, line in enumerate(lines):
            compact = line.replace(" ", "").strip().upper()
            if not _looks_like_mrz(compact):
                continue

            facts.append(
                _candidate(
                    request=request,
                    fact_type="mrz_line",
                    raw_value=compact,
                    normalized_value=compact,
                    confidence=0.78,
                    line_index=index,
                    metadata={
                        "source": "universal_mrz",
                        "review_editable": True,
                        "auto_accept": False,
                        "is_person_fact": False,
                        "needs_human_review": True,
                    },
                )
            )

        return facts[:3]


def _candidate(
    *,
    request: ExtractionRequest,
    fact_type: str,
    raw_value: str,
    normalized_value: str,
    confidence: float,
    line_index: int,
    metadata: dict[str, object],
) -> CandidateFact:
    return CandidateFact.create(
        document_id=DocumentId(request.content.document_id),
        source_id=SourceId(request.content.source_id),
        entity_id=EntityId(request.entity_id),
        fact_type=fact_type,
        source_stage=_SOURCE_STAGE,
        raw_value=raw_value,
        normalized_value=normalized_value,
        confidence=confidence,
        span_ids=(_fallback_span_id(request.content.document_id, line_index),),
        metadata=metadata,
    )


def _fallback_span_id(document_id: DocumentId, line_index: int) -> SpanId:
    return generate_span_id()


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _clean_lines(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        line = _clean_value(line)
        if line and not any(part in line.lower() for part in _BAD_LINE_PARTS):
            result.append(line)
    return result


def _clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    value = value.strip(" \t:;,.|")
    return value.strip()


def _norm(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    value = re.sub(r"[_\-:;,.()\[\]{}©]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _label_matches(line: str, label: str) -> bool:
    label_norm = _norm(label)
    return bool(re.search(rf"(^|\b){re.escape(label_norm)}(\b|$)", line))


def _value_after_label(line: str, label: str) -> str:
    pattern = re.compile(re.escape(label), re.IGNORECASE)
    parts = pattern.split(line, maxsplit=1)
    if len(parts) < 2:
        return ""
    return _clean_value(parts[1])


def _line_is_standalone_label(line: str, label: str) -> bool:
    line_norm = _norm(line)
    label_norm = _norm(label)
    return line_norm == label_norm or line_norm in {label_norm + ":", label_norm + " /"}


def _is_valid_field_value(field: str, value: str) -> bool:
    value = _clean_value(value)
    value_norm = _norm(value)

    if not value_norm:
        return False

    if _is_noise_value(value):
        return False

    if _contains_many_labels(value):
        return False

    if field in _DATE_FIELDS:
        return bool(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", value))

    if field == "sex":
        return value_norm in {"m", "f", "x", "male", "female", "männlich", "maennlich", "weiblich", "masculin", "féminin", "feminin"}

    if field == "height":
        return bool(re.fullmatch(r"\d{2,3}\s?(cm|m)?", value_norm))

    if field == "eye_color":
        return value_norm in {"brown", "blue", "green", "grey", "gray", "black", "braun", "blau", "gruen", "grün", "grau", "schwarz", "marron", "bleu", "vert", "gris", "noir"}

    if field == "passport_number":
        return bool(re.fullmatch(r"[A-Z0-9]{6,12}", value.upper())) and not value_norm.isalpha()

    if field == "iban":
        return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", value.upper()))

    if field == "bic":
        return bool(re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", value.upper())) and value_norm not in _COUNTRY_WORDS

    if field in {"gross_salary", "net_salary"}:
        return bool(re.search(r"\d", value)) and bool(re.search(r"(eur|€)", value_norm))

    if field in {"invoice_number", "customer_number", "tax_id"}:
        return bool(re.search(r"\d", value)) and len(value_norm) >= 4

    if field in {"nationality"}:
        return value_norm.isalpha() and len(value_norm) >= 4 and value_norm not in _NOISE_VALUES

    if field in _TEXT_NAME_FIELDS:
        return _looks_like_human_text_value(value)

    return len(value_norm) >= 2


def _is_valid_pattern_value(fact_type: str, value: str) -> bool:
    if _is_noise_value(value):
        return False

    if fact_type == "date":
        return bool(re.fullmatch(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", value))

    if fact_type == "amount":
        return bool(re.search(r"(EUR|€)", value, re.IGNORECASE))

    if fact_type == "document_number":
        return bool(re.search(r"\d", value)) and not _norm(value).isalpha()

    return True


def _normalize_field_value(field: str, value: str) -> str:
    value = _clean_value(value)
    if field in {"iban", "bic", "passport_number", "document_number", "mrz_line"}:
        return value.upper().replace(" ", "")
    return value


def _is_noise_value(value: str) -> bool:
    value_norm = _norm(value)

    if len(value_norm) < 2:
        return True

    if value_norm in _NOISE_VALUES:
        return True

    if value_norm in _COUNTRY_WORDS:
        return True

    if "<<" in value_norm and not _looks_like_mrz(value.upper().replace(" ", "")):
        return True

    if any(char in value for char in "©[]{}"):
        return True

    letters = re.sub(r"[^a-zA-Z]", "", value)
    if len(letters) >= 7:
        vowels = len(re.findall(r"[aeiouAEIOU]", letters))
        if vowels == 0:
            return True

    return False


def _contains_many_labels(value: str) -> bool:
    value_norm = _norm(value)
    hits = 0

    for labels in _FIELD_LABELS.values():
        for label in labels:
            if _label_matches(value_norm, label):
                hits += 1

    return hits >= 2


def _looks_like_human_text_value(value: str) -> bool:
    value_norm = _norm(value)

    if len(value_norm) < 2:
        return False

    if any(char.isdigit() for char in value_norm):
        return False

    if value_norm in _NOISE_VALUES:
        return False

    if len(value_norm.split()) > 6:
        return False

    letters = re.sub(r"[^a-zA-ZÀ-ÿ ]", "", value)
    return len(letters.strip()) >= 2


def _looks_like_mrz(line: str) -> bool:
    compact = line.replace(" ", "").strip().upper()
    if len(compact) < 25 or len(compact) > 44:
        return False
    if "<" not in compact:
        return False
    return bool(re.fullmatch(r"[A-Z0-9<]{25,44}", compact))


def _line_index_for_match(text: str, position: int) -> int:
    return text[:position].count("\n")


def _candidate_is_safe(fact: CandidateFact) -> bool:
    return _is_valid_field_value(fact.fact_type, fact.normalized_value) or fact.fact_type in {"email", "phone_number", "date", "amount", "document_number", "mrz_line"}


def _dedupe(facts: list[CandidateFact]) -> list[CandidateFact]:
    seen: set[tuple[str, str]] = set()
    result: list[CandidateFact] = []

    for fact in facts:
        key = (fact.fact_type, fact.normalized_value.lower().strip())
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)

    return result
