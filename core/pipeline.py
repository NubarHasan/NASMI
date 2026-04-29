from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from core.event_bus import bus
from core.events import Event, EventType
from core.state_machine import StateMachine, DocumentState
from intelligence.document_classifier import DocumentClassifier, ClassificationResult
from intelligence.field_schema import DocumentType
from intelligence.ner_engine import NEREngine, ExtractedEntities
from intelligence.merge_logic import MergeLogic
from intelligence.smart_suggest import SmartSuggest, SuggestionResult


@dataclass
class PipelineResult:
    document_id: str
    doc_type: DocumentType
    confidence: float
    method: str
    extracted_fields: dict
    missing_required: list[str]
    missing_optional: list[str]
    quality_score: float
    has_expiry: bool
    expiry_date: Optional[str]
    conflicts: dict
    status: str
    suggestions: Optional[SuggestionResult] = None
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class Pipeline:

    def __init__(self):
        self.classifier = DocumentClassifier()
        self.ner = NEREngine()
        self.merge_logic = MergeLogic()
        self.state_machine = StateMachine()
        self.smart_suggest = SmartSuggest()

    def run(self, document_id: str, text: str) -> PipelineResult:
        start = datetime.now()
        errors: list[str] = []

        classification = self._step_classify(text, errors)
        extracted = self._step_extract(text, classification, errors)
        missing = self.classifier.get_missing_fields(
            classification.doc_type, extracted.to_dict()
        )
        quality = extracted.confidence
        merge_result = self._step_merge(extracted, document_id, errors)
        conflicts = merge_result.conflicts if merge_result else {}
        expiry_date = self._step_expiry(extracted, classification)
        suggestions = self._step_suggest(extracted, classification, errors)
        status = self._step_store(errors)

        self._emit_events(document_id, classification, conflicts, quality)

        duration = (datetime.now() - start).total_seconds() * 1000

        return PipelineResult(
            document_id=document_id,
            doc_type=classification.doc_type,
            confidence=classification.confidence,
            method=classification.method,
            extracted_fields=extracted.to_dict(),
            missing_required=missing["required"],
            missing_optional=missing["optional"],
            quality_score=quality,
            has_expiry=classification.has_expiry,
            expiry_date=expiry_date,
            conflicts=conflicts,
            status=status,
            suggestions=suggestions,
            errors=errors,
            duration_ms=round(duration, 2),
        )

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _step_classify(self, text: str, errors: list) -> ClassificationResult:
        try:
            return self.classifier.classify(text)
        except Exception as e:
            errors.append(f"classify: {e}")
            return ClassificationResult(
                doc_type=DocumentType.UNKNOWN,
                confidence=0.0,
                method="failed",
                matched_keywords=[],
                suggested_fields=[],
                has_expiry=False,
            )

    def _step_extract(
        self,
        text: str,
        classification: ClassificationResult,
        errors: list,
    ) -> ExtractedEntities:
        try:
            return self.ner.extract(text, classification.doc_type.value)
        except Exception as e:
            errors.append(f"extract: {e}")
            return ExtractedEntities()

    def _step_merge(
        self,
        extracted: ExtractedEntities,
        document_id: str,
        errors: list,
    ):
        try:
            return self.merge_logic.merge(
                entities_list=[extracted],
                sources=[document_id],
            )
        except Exception as e:
            errors.append(f"merge: {e}")
            return None

    def _step_expiry(
        self,
        extracted: ExtractedEntities,
        classification: ClassificationResult,
    ) -> Optional[str]:
        if not classification.has_expiry:
            return None
        if extracted.expiry_date:
            return extracted.expiry_date
        return extracted.extra.get("expiry_date")

    def _step_suggest(
        self,
        extracted: ExtractedEntities,
        classification: ClassificationResult,
        errors: list,
    ) -> Optional[SuggestionResult]:
        try:
            return self.smart_suggest.analyze(
                fields=extracted.to_dict(),
                doc_type=classification.doc_type,
            )
        except Exception as e:
            errors.append(f"suggest: {e}")
            return None

    def _step_store(self, errors: list) -> str:
        try:
            self.state_machine.transition_document(
                DocumentState.PROCESSING,
                DocumentState.REVIEWED,
            )
            return "REVIEWED"
        except Exception as e:
            errors.append(f"store: {e}")
            return "FAILED"

    def _emit_events(
        self,
        document_id: str,
        classification: ClassificationResult,
        conflicts: dict,
        quality: float,
    ) -> None:
        try:
            bus.publish(
                Event(
                    event_type=EventType.ENTITY_MERGED,
                    payload={
                        "document_id": document_id,
                        "doc_type": classification.doc_type.value,
                        "confidence": classification.confidence,
                        "quality": quality,
                    },
                    source="pipeline",
                )
            )
            if conflicts:
                bus.publish(
                    Event(
                        event_type=EventType.CONFLICT_DETECTED,
                        payload={
                            "document_id": document_id,
                            "conflicts": conflicts,
                        },
                        source="pipeline",
                    )
                )
        except Exception:
            pass
