from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from intelligence.field_schema import DocumentType, FieldSchema, SCHEMAS
from intelligence.field_registry import FIELD_REGISTRY

DATE_CORRECTIONS: list[tuple[str, str]] = [
    (r"(\d{2})-(\d{2})-(\d{4})", r"\1.\2.\3"),
    (r"(\d{2})/(\d{2})/(\d{4})", r"\1.\2.\3"),
    (r"(\d{4})-(\d{2})-(\d{2})", r"\3.\2.\1"),
]


@dataclass
class SuggestionResult:
    missing_fields: list[str]
    corrections: dict[str, str]
    suggested_type: Optional[DocumentType]
    confidence: float
    matched_fields: list[str] = field(default_factory=list)


class SmartSuggest:

    # ── 1. Missing fields ──────────────────────────────────────────────────────

    def get_missing_fields(
        self,
        doc_type: DocumentType,
        extracted_keys: set[str],
    ) -> list[str]:
        schema = SCHEMAS.get(doc_type)
        if not schema:
            return []
        return [f for f in schema.required if f not in extracted_keys]

    # ── 2. Auto corrections ────────────────────────────────────────────────────

    def get_corrections(
        self,
        fields: dict[str, str],
    ) -> dict[str, str]:
        corrections = {}
        for key, value in fields.items():
            definition = FIELD_REGISTRY.get(key)
            if not definition or not value:
                continue
            corrected = self._try_correct(value, definition.regex)
            if corrected and corrected != value:
                corrections[key] = corrected
        return corrections

    def _try_correct(
        self,
        value: str,
        regex: Optional[str],
    ) -> Optional[str]:
        for pattern, replacement in DATE_CORRECTIONS:
            if re.fullmatch(pattern, value.strip()):
                return re.sub(pattern, replacement, value.strip())

        if regex:
            cleaned = re.sub(r"[\s\-_]", "", value)
            if re.fullmatch(regex, cleaned):
                return cleaned

        return None

    # ── 3. Document type suggestion ────────────────────────────────────────────

    def suggest_doc_type(
        self,
        extracted_keys: set[str],
    ) -> tuple[Optional[DocumentType], float, list[str]]:
        best_type: Optional[DocumentType] = None
        best_score: float = 0.0
        best_matched: list[str] = []

        for doc_type, schema in SCHEMAS.items():
            if doc_type == DocumentType.UNKNOWN:
                continue

            all_fields = set(schema.required + schema.optional)
            matched = list(extracted_keys & all_fields)
            score = len(matched) / len(all_fields) if all_fields else 0.0

            if score > best_score:
                best_score = score
                best_type = doc_type
                best_matched = matched

        return best_type, round(best_score, 2), best_matched

    # ── Main entry point ───────────────────────────────────────────────────────

    def analyze(
        self,
        fields: dict[str, str],
        doc_type: DocumentType,
    ) -> SuggestionResult:
        extracted_keys = set(fields.keys())

        if doc_type == DocumentType.UNKNOWN:
            suggested_type, confidence, matched = self.suggest_doc_type(extracted_keys)
        else:
            suggested_type = doc_type
            confidence = 1.0
            matched = list(extracted_keys)

        missing = self.get_missing_fields(
            suggested_type or DocumentType.UNKNOWN, extracted_keys
        )
        corrections = self.get_corrections(fields)

        return SuggestionResult(
            missing_fields=missing,
            corrections=corrections,
            suggested_type=suggested_type,
            confidence=confidence,
            matched_fields=matched,
        )
