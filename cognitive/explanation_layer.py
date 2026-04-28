from dataclasses import dataclass, field
from knowledge.knowledge_objects import KnowledgeObject, FieldType
from cognitive.context_fusion import FusedContext
from cognitive.prediction_engine import Prediction
from core.events import Event, EventType
from core.event_bus import bus


FIELD_LABELS: dict[FieldType, str] = {
    FieldType.IDENTITY: "Identity",
    FieldType.ADDRESS: "Address",
    FieldType.CONTACT: "Contact",
    FieldType.FINANCIAL: "Financial",
    FieldType.LEGAL: "Legal",
    FieldType.EMPLOYMENT: "Employment",
    FieldType.DOCUMENT: "Document",
    FieldType.OTHER: "Other",
}

CONFIDENCE_LABELS: list[tuple[float, str]] = [
    (0.85, "High confidence"),
    (0.60, "Moderate confidence"),
    (0.40, "Low confidence"),
    (0.00, "Very low confidence"),
]

SOURCE_TEMPLATES: dict[str, str] = {
    "ocr": "extracted via OCR from {document_id} (page {page})",
    "ner": "identified by NER engine from {document_id}",
    "manual": "manually entered by user",
    "merged": "merged from multiple sources including {document_id}",
    "default": "sourced from {document_id}",
}


@dataclass
class FieldExplanation:
    field_type: str
    value: str
    reason: str
    confidence: str
    source: str
    trust_score: float

    def to_dict(self) -> dict:
        return {
            "field_type": self.field_type,
            "value": self.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "source": self.source,
            "trust_score": self.trust_score,
        }


@dataclass
class ContextExplanation:
    owner_id: str
    summary: str
    field_notes: list[FieldExplanation] = field(default_factory=list)
    predictions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "owner_id": self.owner_id,
            "summary": self.summary,
            "field_notes": [f.to_dict() for f in self.field_notes],
            "predictions": self.predictions,
        }


class ExplanationLayer:

    def explain_context(
        self,
        context: FusedContext,
        predictions: list[Prediction] | None = None,
    ) -> ContextExplanation:

        field_notes = [self._explain_object(obj) for obj in context.objects]
        summary = self._build_summary(context)
        pred_texts = [p.result for p in predictions] if predictions else []

        explanation = ContextExplanation(
            owner_id=context.owner_id,
            summary=summary,
            field_notes=field_notes,
            predictions=pred_texts,
        )

        bus.publish(
            Event(
                event_type=EventType.PREDICTION_GENERATED,
                payload={
                    "owner_id": context.owner_id,
                    "explained_fields": len(field_notes),
                },
                source="explanation_layer",
            )
        )

        return explanation

    def explain_object(self, obj: KnowledgeObject) -> FieldExplanation:
        return self._explain_object(obj)

    def _explain_object(self, obj: KnowledgeObject) -> FieldExplanation:
        label = FIELD_LABELS.get(obj.field_type, "Unknown")
        confidence = self._confidence_label(obj.confidence.final)
        source = self._source_text(obj)
        reason = (
            f'{label} value "{obj.value}" was {source}. '
            f"Confidence: {confidence} ({obj.confidence.final})."
        )

        return FieldExplanation(
            field_type=obj.field_type.value,
            value=obj.value,
            reason=reason,
            confidence=confidence,
            source=source,
            trust_score=obj.quality.trust_score,
        )

    def _build_summary(self, context: FusedContext) -> str:
        total = len(context.objects)
        clusters = [c.label for c in context.clusters]
        return (
            f"Profile for {context.owner_id} contains {total} data fields "
            f"with an overall trust score of {context.trust_score}. "
            f'Detected life events: {", ".join(clusters) if clusters else "none"}.'
        )

    def _confidence_label(self, score: float) -> str:
        for threshold, label in CONFIDENCE_LABELS:
            if score >= threshold:
                return label
        return "Unknown"

    def _source_text(self, obj: KnowledgeObject) -> str:
        method = obj.provenance.method or "default"
        template = SOURCE_TEMPLATES.get(method, SOURCE_TEMPLATES["default"])
        return template.format(
            document_id=obj.provenance.document_id or "unknown document",
            page=obj.provenance.page,
        )
