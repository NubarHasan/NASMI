from dataclasses import dataclass
from enum import Enum
from typing import Optional

from intelligence.field_schema import DocumentType, detect_type_by_keywords
from intelligence.field_registry import FIELD_REGISTRY


class DocumentIntent(Enum):
    EXTRACT = "extract"
    FILL = "fill"
    MIXED = "mixed"
    UNKNOWN = "unknown"


FORM_SIGNALS = [
    "___",
    "........",
    "[ ]",
    "☐",
    "please fill",
    "bitte ausfüllen",
    "signature:",
    "unterschrift:",
    "date:",
    "datum:",
    "(required)",
    "pflichtfeld",
    "fill in",
    "eintragen",
]

FORM_SIGNAL_THRESHOLD = 3


@dataclass
class ClassificationResult:
    doc_type: DocumentType
    confidence: float
    method: str
    matched_keywords: list[str]
    suggested_fields: list[str]
    has_expiry: bool
    intent: DocumentIntent = DocumentIntent.UNKNOWN


class DocumentClassifier:

    OLLAMA_THRESHOLD = 0.50

    def classify(
        self, text: str, use_ollama_fallback: bool = True
    ) -> ClassificationResult:
        doc_type, confidence, matched = self._keyword_classify(text)

        if confidence < self.OLLAMA_THRESHOLD and use_ollama_fallback:
            doc_type, confidence = self._ollama_classify(text)
            method = "ollama"
        else:
            method = "keyword"

        intent = self._detect_intent(text)
        suggested = self._suggest_fields(doc_type)
        has_expiry = self._check_expiry(doc_type)

        return ClassificationResult(
            doc_type=doc_type,
            confidence=confidence,
            method=method,
            matched_keywords=matched,
            suggested_fields=suggested,
            has_expiry=has_expiry,
            intent=intent,
        )

    # ── Intent Detection ───────────────────────────────────────────────────

    def _detect_intent(self, text: str) -> DocumentIntent:
        text_lower = text.lower()
        signal_hits = sum(1 for s in FORM_SIGNALS if s in text_lower)

        has_real_values = self._has_real_values(text)

        if signal_hits >= FORM_SIGNAL_THRESHOLD and not has_real_values:
            return DocumentIntent.FILL
        if signal_hits >= FORM_SIGNAL_THRESHOLD and has_real_values:
            return DocumentIntent.MIXED
        if has_real_values:
            return DocumentIntent.EXTRACT
        return DocumentIntent.UNKNOWN

    def _has_real_values(self, text: str) -> bool:
        import re

        patterns = [
            r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
            r"\b\d{2}[.\-/]\d{2}[.\-/]\d{4}\b",
            r"\b[A-Z]{1,2}\d{6,9}\b",
            r"\bDE\d{20}\b",
        ]
        return any(re.search(p, text) for p in patterns)

    # ── Keyword Classification ─────────────────────────────────────────────

    def _keyword_classify(self, text: str) -> tuple[DocumentType, float, list[str]]:
        from intelligence.field_schema import SCHEMAS

        text_lower = text.lower()
        scores: dict[DocumentType, list[str]] = {}

        for doc_type, schema in SCHEMAS.items():
            if doc_type == DocumentType.UNKNOWN:
                continue
            hits = [kw for kw in schema.keywords if kw in text_lower]
            if hits:
                scores[doc_type] = hits

        if not scores:
            return DocumentType.UNKNOWN, 0.0, []

        best = max(scores, key=lambda t: len(scores[t]))
        total_keywords = len(SCHEMAS[best].keywords)
        confidence = round(len(scores[best]) / total_keywords, 2)
        return best, min(confidence, 0.99), scores[best]

    def _ollama_classify(self, text: str) -> tuple[DocumentType, float]:
        try:
            from llm.ollama_client import OllamaClient

            client = OllamaClient()
            prompt = (
                f"Classify this document. Return JSON only: "
                f'{{"doc_type": "<type>", "confidence": <0-1>}}\n'
                f"Types: {[t.value for t in DocumentType]}\n\n"
                f"Text (first 500 chars):\n{text[:500]}"
            )
            import json, re

            raw = client.generate(prompt)
            match = re.search(r"\{.*?\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                doc_type = DocumentType(data.get("doc_type", "unknown"))
                confidence = float(data.get("confidence", 0.5))
                return doc_type, confidence
        except Exception:
            pass
        return DocumentType.UNKNOWN, 0.0

    # ── Helpers ────────────────────────────────────────────────────────────

    def _suggest_fields(self, doc_type: DocumentType) -> list[str]:
        from intelligence.field_schema import SCHEMAS

        schema = SCHEMAS.get(doc_type)
        return schema.all_fields() if schema else []

    def _check_expiry(self, doc_type: DocumentType) -> bool:
        from intelligence.field_schema import SCHEMAS

        schema = SCHEMAS.get(doc_type)
        return schema.has_expiry if schema else False

    def get_missing_fields(
        self, doc_type: DocumentType, extracted: dict
    ) -> dict[str, list[str]]:
        from intelligence.field_schema import SCHEMAS

        schema = SCHEMAS.get(doc_type)
        if not schema:
            return {"required": [], "optional": []}
        filled = {k for k, v in extracted.items() if v}
        return {
            "required": [f for f in schema.required if f not in filled],
            "optional": [f for f in schema.optional if f not in filled],
        }
