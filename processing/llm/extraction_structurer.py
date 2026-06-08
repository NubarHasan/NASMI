from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.types import ExtractorId, SpanId
from processing.extraction.candidate_fact import CandidateFact
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.llm.llm_port import LLMPort

_log = logging.getLogger(__name__)

_SOURCE_STAGE = "extraction:llm_structured"
_EXTRACTOR_ID = ExtractorId("llm.extraction_structurer.v1")

_ALLOWED_FACT_TYPES = {
    "document_type",
    "full_name",
    "surname",
    "given_names",
    "father_name",
    "mother_name",
    "date_of_birth",
    "place_of_birth",
    "nationality",
    "sex",
    "passport_number",
    "document_number",
    "id_number",
    "residence_permit_number",
    "date_of_issue",
    "date_of_expiry",
    "issuing_authority",
    "address",
    "city",
    "country",
    "postal_code",
    "phone_number",
    "email",
    "iban",
    "tax_id",
    "social_security_number",
    "employer",
    "job_title",
    "salary",
    "start_date",
    "end_date",
    "invoice_number",
    "amount",
    "currency",
    "mrz_line",
    "eye_color",
    "height",
    "unknown_important_value",
}

_PERSON_FACT_TYPES = {
    "full_name",
    "surname",
    "given_names",
    "father_name",
    "mother_name",
    "date_of_birth",
    "place_of_birth",
    "nationality",
    "sex",
    "address",
    "city",
    "country",
    "postal_code",
    "phone_number",
    "email",
}

_USEFUL_FACT_TYPES = {
    "document_type",
    "full_name",
    "surname",
    "given_names",
    "father_name",
    "mother_name",
    "date_of_birth",
    "place_of_birth",
    "nationality",
    "sex",
    "passport_number",
    "document_number",
    "id_number",
    "residence_permit_number",
    "date_of_issue",
    "date_of_expiry",
    "issuing_authority",
    "address",
    "city",
    "country",
    "postal_code",
    "email",
    "phone_number",
    "iban",
    "employer",
    "job_title",
    "salary",
    "start_date",
    "end_date",
    "invoice_number",
    "amount",
    "currency",
    "mrz_line",
    "eye_color",
    "height",
    "unknown_important_value",
}

_LABELS = {
    "name",
    "surname",
    "given names",
    "date of birth",
    "place of birth",
    "nationality",
    "sex",
    "height",
    "residence",
    "domicile",
    "address",
    "passport",
    "passport no",
    "passport number",
    "authority",
    "issued by",
    "date of issue",
    "date of expiry",
    "expiry date",
    "signature",
    "holder signature",
    "type",
    "code",
    "country code",
    "birth",
    "issue",
    "expiry",
    "reisepass",
    "pass-nr",
    "pass nr",
    "vornamen",
    "geburtstag",
    "staatsangehörigkeit",
    "behörde",
    "augenfarbe",
    "größe",
}

_FIELD_ALIASES = {
    "passport_no": "passport_number",
    "passport_nr": "passport_number",
    "pass_no": "passport_number",
    "pass_nr": "passport_number",
    "passport": "passport_number",
    "document_no": "document_number",
    "document_nr": "document_number",
    "doc_number": "document_number",
    "birth_date": "date_of_birth",
    "dob": "date_of_birth",
    "expiry_date": "date_of_expiry",
    "expiration_date": "date_of_expiry",
    "valid_until": "date_of_expiry",
    "authority": "issuing_authority",
    "issued_by": "issuing_authority",
    "given_name": "given_names",
    "first_name": "given_names",
    "last_name": "surname",
    "family_name": "surname",
    "eye_colour": "eye_color",
    "colour_of_eyes": "eye_color",
    "color_of_eyes": "eye_color",
}


class LLMExtractionStructurer:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def structure(
        self,
        request: ExtractionRequest,
        raw_text: str,
        candidates: list[CandidateFact],
    ) -> ExtractionResult:
        prompt = _build_prompt(raw_text, candidates)
        response = self._llm.complete(
            prompt=prompt,
            context={
                "task": "extraction_structuring",
                "document_id": str(request.content.document_id),
                "source_id": str(request.content.source_id),
                "document_type": request.content.document_type or "unknown",
            },
        )

        if response.has_error:
            _log.warning("LLM extraction structuring failed: %s", response.failure)
            return ExtractionResult.failure(
                document_id=request.content.document_id,
                source_id=request.content.source_id,
                extractor_id=_EXTRACTOR_ID,
                metadata={
                    "strategy": "llm_structuring",
                    "failure": response.failure,
                },
            )

        if response.is_empty:
            return ExtractionResult.failure(
                document_id=request.content.document_id,
                source_id=request.content.source_id,
                extractor_id=_EXTRACTOR_ID,
                metadata={
                    "strategy": "llm_structuring",
                    "failure": "empty_llm_response",
                },
            )

        data = _parse_json(response.raw_text)
        facts_data = data.get("facts") if isinstance(data, dict) else None

        if not isinstance(facts_data, list):
            return ExtractionResult.failure(
                document_id=request.content.document_id,
                source_id=request.content.source_id,
                extractor_id=_EXTRACTOR_ID,
                metadata={
                    "strategy": "llm_structuring",
                    "failure": "invalid_json_schema",
                    "raw_response": response.raw_text[:1500],
                },
            )

        facts = _make_candidate_facts(
            request=request,
            facts_data=facts_data,
            candidates=candidates,
            raw_response=response.raw_text,
        )
        facts = _dedupe(facts)

        if not facts:
            return ExtractionResult.failure(
                document_id=request.content.document_id,
                source_id=request.content.source_id,
                extractor_id=_EXTRACTOR_ID,
                metadata={
                    "strategy": "llm_structuring",
                    "failure": "no_valid_structured_facts",
                    "raw_response": response.raw_text[:1500],
                },
            )

        return ExtractionResult.success(
            document_id=request.content.document_id,
            source_id=request.content.source_id,
            extractor_id=_EXTRACTOR_ID,
            candidate_facts=tuple(facts),
            metadata={
                "strategy": "llm_structuring",
                "structured_candidate_count": len(facts),
                "raw_candidate_count": len(candidates),
                "llm_model_role": "knowledge_recovery",
            },
        )


def _build_prompt(raw_text: str, candidates: list[CandidateFact]) -> str:
    compact_candidates = _compact_candidates(candidates)
    compact_text = _compact_ocr_text(raw_text)

    payload = {
        "text": compact_text,
        "candidates": compact_candidates,
    }

    return (
        "NASMI OCR cleanup. Extract only visible personal/document facts. No invention. No labels as values.\n"
        "Return JSON only: "
        '{"facts":[{"fact_type":"string","value":"string","normalized_value":"string","confidence":0.8,"evidence":"string","reason":"string"}]}\n'
        "Allowed types: "
        f"{sorted(_ALLOWED_FACT_TYPES)}\n"
        "Passport focus: surname, given_names, date_of_birth, nationality, sex, passport_number, document_number, date_of_expiry, issuing_authority, eye_color, height, mrz_line.\n"
        "German hints: Reisepass=passport, Name/Surname=surname, Vornamen=given_names, Geburtstag=date_of_birth, Staatsangehörigkeit=nationality, Behörde=issuing_authority, Pass-Nr=passport_number, Augenfarbe=eye_color, Größe=height.\n"
        "Normalize dates to YYYY-MM-DD when clear. Keep visible value if uncertain. Confidence 0.65-0.95.\n"
        "Input:\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    )


def _compact_candidates(candidates: list[CandidateFact]) -> list[dict[str, Any]]:
    filtered = [
        fact
        for fact in candidates
        if str(fact.fact_type).strip().lower() in _USEFUL_FACT_TYPES
        and not _looks_like_label_only(str(fact.raw_value))
    ]

    if not filtered:
        filtered = [
            fact
            for fact in candidates
            if not _looks_like_label_only(str(fact.raw_value))
        ]

    if not filtered:
        filtered = candidates

    result = []
    for index, fact in enumerate(filtered[:35], start=1):
        result.append(
            {
                "i": index,
                "t": str(fact.fact_type)[:45],
                "v": str(fact.raw_value)[:140],
                "n": str(fact.normalized_value)[:140],
                "c": round(float(fact.confidence), 2),
            }
        )

    return result


def _compact_ocr_text(raw_text: str) -> str:
    text = raw_text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) <= 4500:
        return text

    priority_lines = []
    patterns = (
        r"reisepass",
        r"passport",
        r"surname",
        r"name",
        r"given",
        r"vornamen",
        r"birth",
        r"geburt",
        r"national",
        r"staats",
        r"sex",
        r"geschlecht",
        r"pass",
        r"expiry",
        r"gültig",
        r"authority",
        r"behörde",
        r"augen",
        r"height",
        r"größe",
        r"p<",
        r"[A-Z0-9<]{25,}",
    )

    combined = re.compile("|".join(patterns), re.IGNORECASE)

    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if combined.search(cleaned):
            priority_lines.append(cleaned)

    head = text[:1500]
    tail = text[-1800:]
    middle = "\n".join(priority_lines[:80])

    compact = "\n".join(part for part in (head, middle, tail) if part.strip())
    compact = re.sub(r"\n{3,}", "\n\n", compact).strip()

    return compact[:5200]


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _make_candidate_facts(
    request: ExtractionRequest,
    facts_data: list[Any],
    candidates: list[CandidateFact],
    raw_response: str,
) -> list[CandidateFact]:
    result = []
    fallback_span_ids = _fallback_span_ids(candidates)

    for item in facts_data[:40]:
        if not isinstance(item, dict):
            continue

        fact_type = _clean_fact_type(str(item.get("fact_type") or ""))
        fact_type = _FIELD_ALIASES.get(fact_type, fact_type)

        value = _clean_value(str(item.get("value") or ""))
        normalized_value = _clean_value(str(item.get("normalized_value") or value))
        evidence = _clean_value(str(item.get("evidence") or ""))
        reason = _clean_value(str(item.get("reason") or ""))
        confidence = _safe_confidence(item.get("confidence"))

        if not fact_type or not value or not normalized_value:
            continue

        if fact_type not in _ALLOWED_FACT_TYPES:
            fact_type = "unknown_important_value"

        if _looks_like_label_only(value):
            continue

        if _is_bad_value(value):
            continue

        span_ids = _find_best_span_ids(value, normalized_value, evidence, candidates)
        span_match = "exact_or_partial"

        if not span_ids:
            span_ids = fallback_span_ids
            span_match = "fallback"

        if not span_ids:
            continue

        result.append(
            CandidateFact.create(
                document_id=request.content.document_id,
                source_id=request.content.source_id,
                entity_id=request.entity_id,
                fact_type=fact_type,
                source_stage=_SOURCE_STAGE,
                raw_value=value,
                normalized_value=normalized_value,
                confidence=confidence,
                span_ids=span_ids,
                metadata={
                    "source": "llm_extraction_structurer",
                    "evidence": evidence,
                    "reason": reason,
                    "review_editable": True,
                    "auto_accept": False,
                    "is_person_fact": _is_person_fact(fact_type),
                    "span_match": span_match,
                    "raw_llm_response_preview": raw_response[:800],
                },
            )
        )

    return result


def _find_best_span_ids(
    value: str,
    normalized_value: str,
    evidence: str,
    candidates: list[CandidateFact],
) -> tuple[SpanId, ...]:
    search_values = [
        _normalize_match_text(value),
        _normalize_match_text(normalized_value),
        _normalize_match_text(evidence),
    ]
    search_values = [v for v in search_values if v]

    for candidate in candidates:
        candidate_values = [
            _normalize_match_text(candidate.raw_value),
            _normalize_match_text(candidate.normalized_value),
        ]

        for search_value in search_values:
            for candidate_value in candidate_values:
                if not search_value or not candidate_value:
                    continue
                if search_value == candidate_value:
                    return candidate.span_ids
                if len(search_value) >= 4 and search_value in candidate_value:
                    return candidate.span_ids
                if len(candidate_value) >= 4 and candidate_value in search_value:
                    return candidate.span_ids

    return ()


def _fallback_span_ids(candidates: list[CandidateFact]) -> tuple[SpanId, ...]:
    for candidate in candidates:
        if candidate.span_ids:
            return candidate.span_ids
    return ()


def _normalize_match_text(value: str) -> str:
    value = value or ""
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" \t\r\n:;,.|")
    return value


def _clean_fact_type(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def _clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip(" \t\r\n:;,.|")


def _safe_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.72

    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    if confidence < 0.65:
        return 0.65
    if confidence > 0.95:
        return 0.95
    return confidence


def _looks_like_label_only(value: str) -> bool:
    normalized = value.strip().lower().strip(":;,.|")
    normalized = re.sub(r"\s+", " ", normalized)

    if normalized in _LABELS:
        return True

    if len(normalized) <= 2:
        return True

    if normalized.startswith("/") and len(normalized) < 20:
        return True

    return bool(re.fullmatch(r"[\W_]+", normalized))


def _is_bad_value(value: str) -> bool:
    cleaned = value.strip()

    if not cleaned:
        return True

    if len(cleaned) > 180:
        return True

    lowered = cleaned.lower()

    bad_fragments = {
        "signature",
        "unterschrift",
        "federal republic",
        "bundesrepublik",
        "république",
        "passport passeport",
        "type code",
        "colour of eyes",
        "date of birth",
        "given names",
        "surname",
    }

    if lowered in bad_fragments:
        return True

    return bool(re.fullmatch(r"[\W_]+", cleaned))


def _is_person_fact(fact_type: str) -> bool:
    return fact_type in _PERSON_FACT_TYPES


def _dedupe(facts: list[CandidateFact]) -> list[CandidateFact]:
    seen = set()
    result = []

    for fact in facts:
        key = (
            fact.fact_type.strip().lower(),
            fact.normalized_value.strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)

    return result
