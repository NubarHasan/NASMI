from __future__ import annotations

import contextlib
import json
import logging
import re
from typing import Any

from core.identifiers import generate_candidate_fact_id, generate_evidence_id
from core.types import CandidateFactId, EntityId, EvidenceId
from infrastructure.db.repositories.sqlite_review_repository import (
    SqliteReviewRepository,
)
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.llm.extraction_assistant import ExtractionAssistant
from processing.llm.llm_factory import make_extraction_llm, make_null_llm
from review.review_case import ReviewCase
from review.review_type import ReviewPriority

_log = logging.getLogger(__name__)

_STAGE = "llm_extraction"


class LLMExtractionHandler:
    def handle(self, job: Job) -> None:
        job.advance_stage(_STAGE)

        payload = job.get_payload()
        entity_id = str(payload.get("entity_id") or "").strip()
        document_id = str(payload.get("document_id") or "").strip()
        source_id = str(payload.get("source_id") or "").strip()
        raw_text = str(payload.get("raw_text") or "").strip()

        if not entity_id or not document_id or not raw_text:
            self._record_failure(
                job=job,
                message="missing entity_id, document_id, or raw_text",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
            )
            return

        response_text = self._run_llm(raw_text)
        suggestions = self._parse_suggestions(response_text)

        if not suggestions:
            suggestions = self._fallback_suggestions(raw_text)

        if not suggestions:
            return

        self._persist_review_cases(
            job=job,
            entity_id=entity_id,
            document_id=document_id,
            source_id=source_id,
            suggestions=suggestions,
            response_text=response_text,
        )

    def _run_llm(self, raw_text: str) -> str:
        try:
            llm = make_extraction_llm()
        except Exception:
            llm = make_null_llm()

        assistant = ExtractionAssistant(llm)
        prompt_text = raw_text[:6000]

        try:
            response = assistant.suggest_fields(prompt_text)
        except Exception:
            return ""

        for attr in ("text", "content", "message", "output"):
            value = getattr(response, attr, None)
            if value:
                return str(value)

        try:
            data = response.to_dict()
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return str(response or "")

    def _parse_suggestions(self, response_text: str) -> list[dict[str, Any]]:
        text = str(response_text or "").strip()
        if not text:
            return []

        parsed = self._parse_json(text)
        if parsed:
            return parsed

        suggestions: list[dict[str, Any]] = []

        patterns = [
            r"(?P<field>[A-Za-z_][A-Za-z0-9_ ]{1,40})\s*[:=-]\s*(?P<value>[^\n\r]{2,120})",
            r'"(?P<field>[A-Za-z_][A-Za-z0-9_ ]{1,40})"\s*:\s*"(?P<value>[^"]{2,120})"',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                field = self._clean_field(match.group("field"))
                value = self._clean_value(match.group("value"))

                if field and value:
                    suggestions.append(
                        {
                            "field": field,
                            "value": value,
                            "confidence": 0.72,
                        }
                    )

        return self._dedupe(suggestions)

    def _parse_json(self, text: str) -> list[dict[str, Any]]:
        candidates = [text]

        match = re.search(r"```json\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            candidates.insert(0, match.group(1).strip())

        array_match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if array_match:
            candidates.insert(0, array_match.group(0))

        object_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if object_match:
            candidates.insert(0, object_match.group(0))

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except Exception:
                continue

            if isinstance(data, dict):
                if isinstance(data.get("fields"), list):
                    data = data["fields"]
                elif isinstance(data.get("suggestions"), list):
                    data = data["suggestions"]
                else:
                    data = [
                        {"field": str(key), "value": str(value)}
                        for key, value in data.items()
                        if isinstance(value, (str, int, float))
                    ]

            if not isinstance(data, list):
                continue

            suggestions: list[dict[str, Any]] = []

            for item in data:
                if not isinstance(item, dict):
                    continue

                field = self._clean_field(
                    str(
                        item.get("field")
                        or item.get("field_name")
                        or item.get("fact_type")
                        or item.get("name")
                        or ""
                    )
                )
                value = self._clean_value(
                    str(
                        item.get("value")
                        or item.get("normalized_value")
                        or item.get("raw_value")
                        or item.get("text")
                        or ""
                    )
                )

                try:
                    confidence = float(item.get("confidence", 0.75))
                except Exception:
                    confidence = 0.75

                if field and value:
                    suggestions.append(
                        {
                            "field": field,
                            "value": value,
                            "confidence": max(0.0, min(1.0, confidence)),
                        }
                    )

            return self._dedupe(suggestions)

        return []

    def _fallback_suggestions(self, raw_text: str) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []

        email_match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            raw_text,
        )
        if email_match:
            suggestions.append(
                {
                    "field": "email",
                    "value": email_match.group(0),
                    "confidence": 0.7,
                }
            )

        iban_text = raw_text.replace(" ", "")
        iban_match = re.search(
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
            iban_text,
        )
        if iban_match:
            suggestions.append(
                {
                    "field": "iban",
                    "value": iban_match.group(0),
                    "confidence": 0.68,
                }
            )

        date_match = re.search(
            r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
            raw_text,
        )
        if date_match:
            suggestions.append(
                {
                    "field": "date",
                    "value": date_match.group(0),
                    "confidence": 0.6,
                }
            )

        return self._dedupe(suggestions)

    def _persist_review_cases(
        self,
        job: Job,
        entity_id: str,
        document_id: str,
        source_id: str,
        suggestions: list[dict[str, Any]],
        response_text: str,
    ) -> None:
        db = self._resolve_db()
        if db is None:
            self._record_failure(
                job=job,
                message="database unavailable",
                category=FailureCategory.SYSTEM,
                severity=FailureSeverity.ERROR,
                is_retryable=True,
            )
            return

        repo = SqliteReviewRepository(db)
        created = 0

        for suggestion in suggestions:
            field = self._clean_field(str(suggestion.get("field") or "other"))
            value = self._clean_value(str(suggestion.get("value") or ""))

            if not field or not value:
                continue

            try:
                confidence = float(suggestion.get("confidence", 0.7))
            except Exception:
                confidence = 0.7

            confidence = max(0.0, min(1.0, confidence))

            case = ReviewCase.create(
                entity_id=EntityId(entity_id),
                candidate_fact_id=CandidateFactId(str(generate_candidate_fact_id())),
                fact_type=field,
                raw_value=value,
                normalized_value=value,
                confidence=confidence,
                evidence_ids=(EvidenceId(str(generate_evidence_id())),),
                priority=self._priority_for_confidence(confidence),
                metadata={
                    "job_id": job.job_id,
                    "source": "llm_extraction_handler",
                    "source_stage": "llm",
                    "review_source": "llm",
                    "document_id": document_id,
                    "source_id": source_id,
                    "llm_response_preview": response_text[:1000],
                },
            )

            repo.save(case)
            created += 1

        with contextlib.suppress(Exception):
            db.connection.commit()

        _log.info("job %r: created %d LLM review cases", job.job_id, created)

    def _priority_for_confidence(self, confidence: float) -> ReviewPriority:
        if confidence < 0.6 and hasattr(ReviewPriority, "HIGH"):
            return ReviewPriority.HIGH
        if confidence < 0.8 and hasattr(ReviewPriority, "NORMAL"):
            return ReviewPriority.NORMAL
        if hasattr(ReviewPriority, "LOW"):
            return ReviewPriority.LOW
        return list(ReviewPriority)[0]

    def _clean_field(self, value: str) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"[^a-z0-9_ ]", "", text)
        text = re.sub(r"\s+", "_", text)
        return text[:80]

    def _clean_value(self, value: str) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text[:500]

    def _dedupe(self, suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        result: list[dict[str, Any]] = []

        for item in suggestions:
            field = self._clean_field(str(item.get("field") or ""))
            value = self._clean_value(str(item.get("value") or ""))

            key = (field.lower(), value.lower())
            if not field or not value or key in seen:
                continue

            seen.add(key)
            result.append(
                {
                    "field": field,
                    "value": value,
                    "confidence": item.get("confidence", 0.7),
                }
            )

        return result[:20]

    def _resolve_db(self) -> Any | None:
        try:
            from ui.services.api_client import _get_db

            return _get_db()
        except Exception:
            return None

    def _record_failure(
        self,
        job: Job,
        message: str,
        category: FailureCategory,
        severity: FailureSeverity,
        is_retryable: bool,
    ) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=_STAGE,
            category=category,
            source=FailureSource.SYSTEM,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=False,
        )
        job.context.failures.add(failure)
        _log.error("job %r: %s", job.job_id, message)
