from dataclasses import dataclass
from typing import Optional

from intelligence.field_schema import DocumentType, detect_type_by_keywords
from intelligence.field_registry import FIELD_REGISTRY


@dataclass
class ClassificationResult:
    doc_type: DocumentType
    confidence: float
    method: str
    matched_keywords: list[str]
    suggested_fields: list[str]
    has_expiry: bool


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

        suggested = self._suggest_fields(doc_type)
        has_expiry = self._check_expiry(doc_type)

        return ClassificationResult(
            doc_type=doc_type,
            confidence=confidence,
            method=method,
            matched_keywords=matched,
            suggested_fields=suggested,
            has_expiry=has_expiry,
        )

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

        best = max(scores, key=lambda k: len(scores[k]))
        total_kw = len(SCHEMAS[best].keywords)
        confidence = round(len(scores[best]) / total_kw, 2)

        return best, confidence, scores[best]

    def _ollama_classify(self, text: str) -> tuple[DocumentType, float]:
        try:
            from llm.ollama_client import OllamaClient
            from intelligence.field_schema import SCHEMAS

            client = OllamaClient()
            types = [t.value for t in DocumentType if t != DocumentType.UNKNOWN]
            prompt = (
                f"Classify this document into one of: {types}\n"
                f"Reply with ONLY the type value, nothing else.\n\n"
                f"Document text (first 500 chars):\n{text[:500]}"
            )
            response = client.generate(prompt).strip().lower()

            for doc_type in DocumentType:
                if doc_type.value == response:
                    return doc_type, 0.75

            return DocumentType.UNKNOWN, 0.0

        except Exception:
            return DocumentType.UNKNOWN, 0.0

    def _suggest_fields(self, doc_type: DocumentType) -> list[str]:
        from intelligence.field_schema import SCHEMAS

        schema = SCHEMAS.get(doc_type)
        if not schema:
            return []
        return schema.required + schema.optional

    def _check_expiry(self, doc_type: DocumentType) -> bool:
        from intelligence.field_schema import SCHEMAS

        schema = SCHEMAS.get(doc_type)
        return schema.has_expiry if schema else False

    def batch_classify(self, texts: list[str]) -> list[ClassificationResult]:
        return [self.classify(t) for t in texts]

    def get_missing_fields(
        self,
        doc_type: DocumentType,
        extracted: dict,
    ) -> dict[str, list[str]]:
        from intelligence.field_schema import SCHEMAS

        schema = SCHEMAS.get(doc_type)
        if not schema:
            return {"required": [], "optional": []}

        missing_required = [f for f in schema.required if not extracted.get(f)]
        missing_optional = [f for f in schema.optional if not extracted.get(f)]

        return {
            "required": missing_required,
            "optional": missing_optional,
        }

    def get_field_labels(
        self,
        fields: list[str],
        language: str = "en",
    ) -> dict[str, str]:
        labels = {}
        for key in fields:
            definition = FIELD_REGISTRY.get(key)
            if definition:
                labels[key] = (
                    definition.label_de if language == "de" else definition.label_en
                )
            else:
                labels[key] = key
        return labels
