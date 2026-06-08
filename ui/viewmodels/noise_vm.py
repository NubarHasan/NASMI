from __future__ import annotations

import contextlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from infrastructure.db.repositories.sqlite_noise_repository import (
    NoiseItem,
    SqliteNoiseRepository,
)
from processing.llm.llm_factory import make_extraction_llm
from ui.services.api_client import _get_db


@dataclass(frozen=True)
class NoiseActionResult:
    success: bool
    message: str = ""
    error: str = ""


_ALLOWED_FACT_TYPES = {
    "given_names",
    "surname",
    "full_name",
    "date_of_birth",
    "place_of_birth",
    "nationality",
    "sex",
    "address",
    "passport_number",
    "document_number",
    "date_of_issue",
    "date_of_expiry",
    "expiry_date",
    "issue_date",
    "issuing_authority",
    "email",
    "phone_number",
    "employer",
    "employee",
    "job_title",
    "start_date",
    "salary",
    "working_hours",
    "amount",
    "date",
    "other",
}


_FIELD_ALIASES = {
    "vorname": "given_names",
    "vornamen": "given_names",
    "given_name": "given_names",
    "first_name": "given_names",
    "firstname": "given_names",
    "familienname": "surname",
    "nachname": "surname",
    "last_name": "surname",
    "lastname": "surname",
    "name": "surname",
    "geburtsdatum": "date_of_birth",
    "birth_date": "date_of_birth",
    "dob": "date_of_birth",
    "geburtsort": "place_of_birth",
    "birth_place": "place_of_birth",
    "staatsangehörigkeit": "nationality",
    "nationalität": "nationality",
    "geschlecht": "sex",
    "anschrift": "address",
    "adresse": "address",
    "passnummer": "passport_number",
    "reisepassnummer": "passport_number",
    "passport_no": "passport_number",
    "document_no": "document_number",
    "dokumentnummer": "document_number",
    "ausstellende_behörde": "issuing_authority",
    "ausstellende behörde": "issuing_authority",
    "behörde": "issuing_authority",
    "gültig_bis": "date_of_expiry",
    "gueltig_bis": "date_of_expiry",
    "valid_until": "date_of_expiry",
    "ablaufdatum": "date_of_expiry",
    "ausstellungsdatum": "date_of_issue",
    "issued_at": "date_of_issue",
    "arbeitgeber": "employer",
    "arbeitnehmer": "employee",
    "berufsbezeichnung": "job_title",
    "beginn": "start_date",
    "gehalt": "salary",
    "vergütung": "salary",
    "arbeitszeit": "working_hours",
    "telefon": "phone_number",
    "telefonnummer": "phone_number",
    "betrag": "amount",
    "datum": "date",
}


class NoiseVM:
    def __init__(self) -> None:
        self._db = _get_db()
        self._repo = SqliteNoiseRepository(self._db)

    def count_open(self) -> int:
        try:
            return self._repo.count_open()
        except Exception:
            return 0

    def load_open(self, limit: int = 10) -> tuple[NoiseItem, ...]:
        try:
            return self._repo.list_open(limit=limit)
        except Exception:
            return ()

    def load_all(self, limit: int = 50) -> tuple[NoiseItem, ...]:
        try:
            return self._repo.list_all(limit=limit)
        except Exception:
            return ()

    def ignore(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.update_status(noise_id, "ignored")
            return NoiseActionResult(success=True, message="Noise item ignored")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def mark_reviewed(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.update_status(noise_id, "reviewed")
            return NoiseActionResult(success=True, message="Noise item reviewed")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def reopen(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.update_status(noise_id, "open")
            return NoiseActionResult(success=True, message="Noise item reopened")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def delete(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.delete(noise_id)
            return NoiseActionResult(success=True, message="Noise item deleted")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def save_edit(
        self,
        noise_id: str,
        raw_text: str,
        reason: str,
        confidence: float,
        metadata_text: str,
    ) -> NoiseActionResult:
        try:
            raw_text = raw_text.strip()
            reason = reason.strip()

            if not raw_text:
                return NoiseActionResult(success=False, error="Raw text is empty")

            if not reason:
                return NoiseActionResult(success=False, error="Reason is empty")

            metadata: dict[str, Any] = {}
            if metadata_text.strip():
                parsed = json.loads(metadata_text)
                if not isinstance(parsed, dict):
                    return NoiseActionResult(
                        success=False,
                        error="Metadata must be a JSON object",
                    )
                metadata = parsed

            self._repo.update_text(
                noise_id=noise_id,
                raw_text=raw_text,
                reason=reason,
                confidence=confidence,
                metadata=metadata,
            )
            return NoiseActionResult(success=True, message="Noise item saved")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def process_with_llm(self, noise_id: str) -> NoiseActionResult:
        try:
            item = self._repo.get(noise_id)
            if item is None:
                return NoiseActionResult(success=False, error="Noise item not found")

            if item.status == "processing":
                return NoiseActionResult(
                    success=False, error="Item is already processing"
                )

            entity_id = str(item.entity_id or "").strip()
            if not entity_id:
                return NoiseActionResult(
                    success=False, error="Noise item has no entity_id"
                )

            raw_text = str(item.raw_text or "").strip()
            if not raw_text:
                return NoiseActionResult(success=False, error="Noise text is empty")

            self._repo.update_status(noise_id, "processing")

            facts = self._extract_clean_facts_with_llm(raw_text)

            if not facts:
                facts = self._fallback_extract_facts(raw_text)

            facts = self._clean_facts(facts)

            if not facts:
                self._repo.update_status(noise_id, "failed")
                return NoiseActionResult(
                    success=False,
                    error="LLM did not return usable facts",
                )

            inserted = self._insert_review_cases(
                item=item,
                entity_id=entity_id,
                facts=facts,
            )

            if inserted <= 0:
                self._repo.update_status(noise_id, "failed")
                return NoiseActionResult(
                    success=False,
                    error="No review cases were created",
                )

            metadata = dict(item.metadata)
            metadata["llm_processed_at"] = _now_iso()
            metadata["llm_created_review_cases"] = inserted
            metadata["llm_extracted_facts"] = facts

            self._repo.update_text(
                noise_id=item.noise_id,
                raw_text=item.raw_text,
                reason=item.reason,
                confidence=item.confidence,
                metadata=metadata,
            )
            self._repo.update_status(noise_id, "promoted")

            return NoiseActionResult(
                success=True,
                message=f"LLM created {inserted} review cases",
            )

        except Exception as exc:
            with contextlib.suppress(Exception):
                self._repo.update_status(noise_id, "failed")
            return NoiseActionResult(success=False, error=str(exc))

    def create_test_noise(self) -> NoiseActionResult:
        try:
            self._repo.create(
                raw_text="Unclear German OCR fragment: Aufenthaltstitel ... gültig bis ...",
                reason="Low confidence OCR fragment needs human review",
                stage="extraction",
                confidence=0.35,
                metadata={
                    "source": "manual_test",
                    "language": "de",
                },
            )
            return NoiseActionResult(success=True, message="Test noise item created")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def _extract_clean_facts_with_llm(self, raw_text: str) -> list[dict[str, Any]]:
        prompt = _build_llm_prompt(raw_text)

        llm = make_extraction_llm()
        response = _call_llm(llm, prompt)
        return _parse_llm_facts(response)

    def _fallback_extract_facts(self, raw_text: str) -> list[dict[str, Any]]:
        facts: list[dict[str, Any]] = []
        text = raw_text.replace("\n", " ")

        email = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I)
        if email:
            facts.append(_fact("email", email.group(0), 0.90))

        phone = re.search(r"(?:\+49|0049|0)\s?\d{2,5}[\s/-]?\d{3,12}", text)
        if phone:
            facts.append(_fact("phone_number", phone.group(0), 0.70))

        date_matches = re.findall(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", text)
        if date_matches:
            facts.append(_fact("date", date_matches[0], 0.65))

        passport = re.search(r"\b[A-Z0-9]{7,10}\b", text)
        if passport and re.search(r"pass|passport|reisepass", text, re.I):
            facts.append(_fact("passport_number", passport.group(0), 0.70))

        return facts

    def _clean_facts(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for item in facts:
            fact_type = _canonical_fact_type(str(item.get("fact_type") or "other"))
            value = str(
                item.get("normalized_value")
                or item.get("value")
                or item.get("raw_value")
                or ""
            ).strip()

            if not value:
                continue

            if len(value) < 2:
                continue

            confidence = _safe_float(item.get("confidence"), 0.72)
            confidence = max(0.50, min(0.99, confidence))

            key = (fact_type, value.lower())
            if key in seen:
                continue

            seen.add(key)
            cleaned.append(
                {
                    "fact_type": fact_type,
                    "raw_value": value,
                    "normalized_value": value,
                    "confidence": confidence,
                }
            )

        return cleaned

    def _insert_review_cases(
        self,
        item: NoiseItem,
        entity_id: str,
        facts: list[dict[str, Any]],
    ) -> int:
        conn = self._db.connection
        inserted = 0

        for fact in facts:
            fact_type = str(fact["fact_type"])
            raw_value = str(fact["raw_value"])
            normalized_value = str(fact["normalized_value"])
            confidence = float(fact["confidence"])

            if _review_case_exists(
                conn=conn,
                entity_id=entity_id,
                fact_type=fact_type,
                normalized_value=normalized_value,
            ):
                continue

            review_case_id = f"RC-{uuid.uuid4().hex.upper()}"
            candidate_fact_id = f"CF-LLM-{uuid.uuid4().hex.upper()}"

            conn.execute(
                """
                INSERT INTO review_cases (
                    review_case_id,
                    entity_id,
                    candidate_fact_id,
                    fact_type,
                    raw_value,
                    normalized_value,
                    confidence,
                    evidence_ids,
                    status,
                    priority,
                    created_at,
                    assigned_to,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_case_id,
                    entity_id,
                    candidate_fact_id,
                    fact_type,
                    raw_value,
                    normalized_value,
                    confidence,
                    json.dumps([], ensure_ascii=False),
                    "PENDING",
                    "MEDIUM",
                    _now_iso(),
                    None,
                    json.dumps(
                        {
                            "source": "noise_llm_cleanup",
                            "noise_id": item.noise_id,
                            "document_id": item.document_id,
                            "source_id": item.source_id,
                            "stage": item.stage,
                            "needs_human_review": True,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            inserted += 1

        conn.commit()
        return inserted


def _build_llm_prompt(raw_text: str) -> str:
    return f"""
You are an information extraction engine for NASMI.

Extract only real personal/document facts from the OCR text.
Ignore labels, menus, headers, random OCR fragments, and repeated noise.

Return ONLY valid JSON.
Do not add markdown.
Do not explain.

JSON schema:
{{
  "facts": [
    {{
      "fact_type": "given_names | surname | full_name | date_of_birth | place_of_birth | nationality | sex | address | passport_number | document_number | date_of_issue | date_of_expiry | issuing_authority | email | phone_number | employer | employee | job_title | start_date | salary | working_hours | amount | date | other",
      "value": "clean value",
      "confidence": 0.0
    }}
  ]
}}

OCR text:
{raw_text}
""".strip()


def _call_llm(llm: Any, prompt: str) -> str:
    for method_name in ("generate", "complete", "invoke", "__call__"):
        method = getattr(llm, method_name, None)
        if method is None:
            continue

        result = method(prompt)

        if isinstance(result, str):
            return result

        if hasattr(result, "text"):
            return str(result.text)

        if hasattr(result, "content"):
            return str(result.content)

        return str(result)

    raise RuntimeError("LLM adapter has no supported call method")


def _parse_llm_facts(response: str) -> list[dict[str, Any]]:
    text = str(response or "").strip()

    if not text:
        return []

    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)

    parsed = json.loads(text)

    if isinstance(parsed, dict):
        facts = parsed.get("facts")
        if isinstance(facts, list):
            return [x for x in facts if isinstance(x, dict)]

    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]

    return []


def _canonical_fact_type(value: str) -> str:
    key = value.strip().lower().replace("-", "_")

    if key in _FIELD_ALIASES:
        key = _FIELD_ALIASES[key]

    if key in _ALLOWED_FACT_TYPES:
        return key

    return "other"


def _fact(fact_type: str, value: str, confidence: float) -> dict[str, Any]:
    return {
        "fact_type": fact_type,
        "raw_value": value,
        "normalized_value": value,
        "confidence": confidence,
    }


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _review_case_exists(
    conn: Any,
    entity_id: str,
    fact_type: str,
    normalized_value: str,
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM review_cases
        WHERE entity_id = ?
          AND fact_type = ?
          AND LOWER(normalized_value) = LOWER(?)
          AND status IN ('PENDING', 'ASSIGNED', 'IN_REVIEW')
        LIMIT 1
        """,
        (entity_id, fact_type, normalized_value),
    ).fetchone()

    return row is not None
