from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from core.event_bus import bus
from core.events import Event, EventType
from core.state_machine import StateMachine, DocumentState
from core.document_loader import DocumentLoader
from core.text_extractor import TextExtractor
from intelligence.ocr_engine import OCREngine
from intelligence.document_classifier import (
    DocumentClassifier,
    ClassificationResult,
    DocumentIntent,
)
from intelligence.field_schema import DocumentType
from intelligence.ner_engine import NEREngine, ExtractedEntities
from intelligence.form_detector import FormDetector
from intelligence.merge_logic import MergeLogic
from intelligence.smart_suggest import SmartSuggest, SuggestionResult
from intelligence.provenance_tracker import ProvenanceTracker


@dataclass
class PipelineResult:
    document_id: str
    doc_type: DocumentType
    intent: DocumentIntent
    confidence: float
    method: str
    extracted_fields: dict
    missing_required: list[str]
    missing_optional: list[str]
    form_fields: list[dict]
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
        self.loader = DocumentLoader()
        self.text_extract = TextExtractor()
        self.ocr = OCREngine()
        self.classifier = DocumentClassifier()
        self.ner = NEREngine()
        self.form_detect = FormDetector()
        self.merge_logic = MergeLogic()
        self.state_machine = StateMachine()
        self.smart_suggest = SmartSuggest()
        self.provenance = ProvenanceTracker()

    def run(self, file_path: str, document_id: str) -> PipelineResult:
        start = datetime.now()
        errors: list[str] = []

        # ── 1. Load ────────────────────────────────────────────────────────
        loaded = self._step_load(file_path, errors)
        if not loaded:
            return self._failed_result(document_id, errors, start)

        # ── 2. Extract Text ────────────────────────────────────────────────
        text = self._step_text(loaded, file_path, errors)

        # ── 3. Classify + Detect Intent ────────────────────────────────────
        classification = self._step_classify(text, errors)

        # ── 4. Route by Intent ─────────────────────────────────────────────
        extracted = ExtractedEntities()
        form_fields = []

        if classification.intent == DocumentIntent.FILL:
            form_fields = self._step_detect_form(text, errors)

        elif classification.intent == DocumentIntent.EXTRACT:
            extracted = self._step_extract(text, classification, errors)

        elif classification.intent == DocumentIntent.MIXED:
            extracted = self._step_extract(text, classification, errors)
            form_fields = self._step_detect_form(text, errors)

        else:
            extracted = self._step_extract(text, classification, errors)

        # ── 5. Post-processing (only for EXTRACT / MIXED) ──────────────────
        missing = self.classifier.get_missing_fields(
            classification.doc_type, extracted.to_dict()
        )
        conflicts = {}
        if classification.intent != DocumentIntent.FILL:
            merge_result = self._step_merge(extracted, document_id, errors)
            conflicts = merge_result.conflicts if merge_result else {}

        expiry_date = self._step_expiry(extracted, classification)
        suggestions = self._step_suggest(extracted, classification, errors)

        # ── 6. Provenance ──────────────────────────────────────────────────
        self._step_provenance(loaded, document_id, classification)

        # ── 7. State + Events ──────────────────────────────────────────────
        status = self._step_state(classification.intent, errors)
        self._emit_events(document_id, classification, conflicts, extracted.confidence)

        duration = (datetime.now() - start).total_seconds() * 1000

        return PipelineResult(
            document_id=document_id,
            doc_type=classification.doc_type,
            intent=classification.intent,
            confidence=classification.confidence,
            method=classification.method,
            extracted_fields=extracted.to_dict(),
            missing_required=missing["required"],
            missing_optional=missing["optional"],
            form_fields=form_fields,
            quality_score=extracted.confidence,
            has_expiry=classification.has_expiry,
            expiry_date=expiry_date,
            conflicts=conflicts,
            status=status,
            suggestions=suggestions,
            errors=errors,
            duration_ms=round(duration, 2),
        )

    # ── Steps ──────────────────────────────────────────────────────────────

    def _step_load(self, file_path: str, errors: list):
        try:
            return self.loader.load(file_path)
        except Exception as e:
            errors.append(f"load: {e}")
            return None

    def _step_text(self, loaded, file_path: str, errors: list) -> str:
        try:
            if loaded.file_type == "pdf":
                result = self.text_extract.extract(loaded)
                if result.full_text.strip():
                    return result.full_text
            return self.ocr.extract(file_path).get("text", "")
        except Exception as e:
            errors.append(f"text: {e}")
            return ""

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
                intent=DocumentIntent.UNKNOWN,
            )

    def _step_extract(
        self, text: str, classification: ClassificationResult, errors: list
    ) -> ExtractedEntities:
        try:
            return self.ner.extract(text, classification.doc_type.value)
        except Exception as e:
            errors.append(f"extract: {e}")
            return ExtractedEntities()

    def _step_detect_form(self, text: str, errors: list) -> list[dict]:
        try:
            result = self.form_detect.detect(text)
            return result if isinstance(result, list) else []
        except Exception as e:
            errors.append(f"form_detect: {e}")
            return []

    def _step_merge(self, extracted: ExtractedEntities, document_id: str, errors: list):
        try:
            return self.merge_logic.merge(
                entities_list=[extracted],
                sources=[document_id],
            )
        except Exception as e:
            errors.append(f"merge: {e}")
            return None

    def _step_expiry(
        self, extracted: ExtractedEntities, classification: ClassificationResult
    ) -> Optional[str]:
        if not classification.has_expiry:
            return None
        return extracted.expiry_date or extracted.extra.get("expiry_date")

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

    def _step_provenance(
        self, loaded, document_id: str, classification: ClassificationResult
    ) -> None:
        try:
            self.provenance.record(
                file_hash=loaded.file_hash,
                filename=loaded.filename,
                source=document_id,
                action="pipeline_processed",
                details={
                    "doc_type": classification.doc_type.value,
                    "intent": classification.intent.value,
                    "method": classification.method,
                },
            )
        except Exception:
            pass

    def _step_state(self, intent: DocumentIntent, errors: list) -> str:
        try:
            if intent == DocumentIntent.FILL:
                self.state_machine.transition_document(
                    DocumentState.PROCESSING,
                    DocumentState.REVIEWED,
                )
                return "AWAITING_FILL"
            self.state_machine.transition_document(
                DocumentState.PROCESSING,
                DocumentState.REVIEWED,
            )
            return "REVIEWED"
        except Exception as e:
            errors.append(f"state: {e}")
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
                        "intent": classification.intent.value,
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
                        payload={"document_id": document_id, "conflicts": conflicts},
                        source="pipeline",
                    )
                )
        except Exception:
            pass

    def _failed_result(
        self, document_id: str, errors: list, start: datetime
    ) -> PipelineResult:
        duration = (datetime.now() - start).total_seconds() * 1000
        return PipelineResult(
            document_id=document_id,
            doc_type=DocumentType.UNKNOWN,
            intent=DocumentIntent.UNKNOWN,
            confidence=0.0,
            method="failed",
            extracted_fields={},
            missing_required=[],
            missing_optional=[],
            form_fields=[],
            quality_score=0.0,
            has_expiry=False,
            expiry_date=None,
            conflicts={},
            status="FAILED",
            errors=errors,
            duration_ms=round(duration, 2),
        )
