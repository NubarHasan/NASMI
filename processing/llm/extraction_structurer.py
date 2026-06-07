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
    "unknown_important_value",
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
                    "raw_response": response.raw_text[:2000],
                },
            )

        facts = _make_candidate_facts(
            request, facts_data, candidates, response.raw_text
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
                    "raw_response": response.raw_text[:2000],
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
                "llm_model_role": "knowledge_verification",
            },
        )


def _build_prompt(raw_text: str, candidates: list[CandidateFact]) -> str:
    compact_candidates = []

    useful_fact_types = {
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
    }

    filtered = [
        fact
        for fact in candidates
        if str(fact.fact_type).strip().lower() in useful_fact_types
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

    for index, fact in enumerate(filtered[:35], start=1):
        compact_candidates.append(
            {
                "i": index,
                "type": str(fact.fact_type)[:40],
                "value": str(fact.raw_value)[:120],
                "normalized": str(fact.normalized_value)[:120],
                "confidence": round(float(fact.confidence), 2),
            }
        )

    payload = {
        "ocr_text": raw_text[:2200],
        "candidate_facts": compact_candidates,
    }

    return (
        "Extract clean personal and document facts from OCR and candidate facts.\n"
        "Use only supported values from input.\n"
        "Do not invent values.\n"
        "Do not return labels as values.\n"
        "Return only valid JSON.\n"
        "Schema:\n"
        '{"facts":[{"fact_type":"string","value":"string","normalized_value":"string","confidence":0.8,"evidence":"string","reason":"string"}]}\n'
        "Allowed fact types:\n"
        f"{sorted(_ALLOWED_FACT_TYPES)}\n"
        "Input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


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

    for item in facts_data:
        if not isinstance(item, dict):
            continue

        fact_type = _clean_fact_type(str(item.get("fact_type") or ""))
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

        span_ids = _find_best_span_ids(value, normalized_value, evidence, candidates)
        if not span_ids:
            span_ids = fallback_span_ids

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
                    "raw_llm_response_preview": raw_response[:1000],
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
        confidence = 0.65

    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def _looks_like_label_only(value: str) -> bool:
    normalized = value.strip().lower().strip(":;,.|")

    labels = {
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
    }

    if normalized in labels:
        return True

    if len(normalized) <= 2:
        return True

    return bool(normalized.startswith("/") and len(normalized) < 20)


def _is_person_fact(fact_type: str) -> bool:
    return fact_type in {
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
