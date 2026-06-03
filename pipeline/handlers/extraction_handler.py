from __future__ import annotations

import logging

from core.guards import require
from core.types import DocumentId, EntityId, LanguageCode, SourceId
from pipeline.artifact import (
    ArtifactType,
    DocumentArtifact,
    ExtractionArtifact,
    OcrArtifact,
)
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.extraction.extractable_content import ExtractableContent
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.extraction.extraction_service import ExtractionService

_log = logging.getLogger(__name__)

_STAGE = "extraction"


class ExtractionHandler:

    def __init__(self, extraction_service: ExtractionService) -> None:
        require(
            isinstance(extraction_service, ExtractionService),
            "extraction_service must be an ExtractionService",
        )
        self._service = extraction_service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        ocr_artifact = self._resolve_ocr_artifact(job)
        if ocr_artifact is None:
            return

        doc_artifact = self._resolve_document_artifact(job, ocr_artifact)
        if doc_artifact is None:
            return

        request = self._build_request(job, ocr_artifact, doc_artifact)
        if request is None:
            return

        result = self._run_extraction(job, ocr_artifact, request)
        if result is None:
            return

        self._emit_artifact(job, ocr_artifact, result)

    def _resolve_ocr_artifact(self, job: Job) -> OcrArtifact | None:
        candidates = job.context.artifacts.by_type(ArtifactType.OCR)
        if not candidates:
            self._record_failure(
                job,
                message="no OcrArtifact in context",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=False,
            )
            return None
        artifact = candidates[-1]
        if not isinstance(artifact, OcrArtifact):
            self._record_failure(
                job,
                message=f"expected OcrArtifact, got {type(artifact).__name__}",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=False,
            )
            return None
        return artifact

    def _resolve_document_artifact(
        self,
        job: Job,
        ocr_artifact: OcrArtifact,
    ) -> DocumentArtifact | None:
        for artifact_id in ocr_artifact.source_artifact_ids:
            artifact = job.context.artifacts.get(artifact_id)
            if isinstance(artifact, DocumentArtifact):
                return artifact
        self._record_failure(
            job,
            message="no DocumentArtifact found in OcrArtifact.source_artifact_ids",
            category=FailureCategory.VALIDATION,
            severity=FailureSeverity.ERROR,
            is_retryable=False,
            requires_review=True,
            artifact_ids=(ocr_artifact.artifact_id,),
        )
        return None

    def _build_request(
        self,
        job: Job,
        ocr_artifact: OcrArtifact,
        doc_artifact: DocumentArtifact,
    ) -> ExtractionRequest | None:
        try:
            ocr_snapshot = ocr_artifact.snapshot
            doc_snapshot = doc_artifact.snapshot

            require(
                "entity_id" in doc_snapshot,
                "DocumentArtifact snapshot missing entity_id",
            )

            entity_id = EntityId(doc_snapshot["entity_id"])
            full_text: str = ocr_snapshot.get("full_text") or ""
            document_type: str | None = doc_snapshot.get("doc_type") or None
            language: LanguageCode | None = doc_snapshot.get("language") or None

            content = ExtractableContent(
                source_id=SourceId(ocr_artifact.source_id),
                document_id=DocumentId(ocr_artifact.document_id),
                document_type=document_type,
                language=language,
                raw_text=full_text,
                normalized_text=full_text.strip(),
                spatial_data=None,
                extraction_hints=(),
            )

            return ExtractionRequest.create(
                entity_id=entity_id,
                content=content,
            )

        except Exception as exc:
            _log.exception("job %r: failed to build ExtractionRequest", job.job_id)
            self._record_failure(
                job,
                message=f"failed to build ExtractionRequest: {exc}",
                category=FailureCategory.EXTRACTION,
                severity=FailureSeverity.ERROR,
                is_retryable=True,
                requires_review=False,
                artifact_ids=(ocr_artifact.artifact_id,),
            )
            return None

    def _run_extraction(
        self,
        job: Job,
        ocr_artifact: OcrArtifact,
        request: ExtractionRequest,
    ) -> ExtractionResult | None:
        try:
            result = self._service.extract(request)
            if not result.succeeded:
                self._record_failure(
                    job,
                    message=str(
                        result.metadata.get("reason", "extraction returned failure")
                    ),
                    category=FailureCategory.EXTRACTION,
                    severity=FailureSeverity.WARNING,
                    is_retryable=True,
                    requires_review=False,
                    artifact_ids=(ocr_artifact.artifact_id,),
                )
                return None
            return result
        except Exception as exc:
            _log.exception("job %r: ExtractionService raised unexpectedly", job.job_id)
            self._record_failure(
                job,
                message=f"ExtractionService raised: {exc}",
                category=FailureCategory.EXTRACTION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(ocr_artifact.artifact_id,),
            )
            return None

    def _emit_artifact(
        self,
        job: Job,
        ocr_artifact: OcrArtifact,
        result: ExtractionResult,
    ) -> None:
        artifact = ExtractionArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            document_id=str(result.document_id),
            source_id=str(result.source_id),
            extractor_id=str(result.extractor_id),
            candidate_fact_count=result.candidate_count,
            mean_confidence=result.mean_confidence,
            snapshot=result.to_dict(),
            source_artifact_ids=(ocr_artifact.artifact_id,),
        )
        job.context.artifacts.add(artifact)
        _log.info(
            "job %r: ExtractionArtifact emitted — %d facts, confidence=%.4f",
            job.job_id,
            artifact.candidate_fact_count,
            artifact.mean_confidence,
        )

    def _record_failure(
        self,
        job: Job,
        message: str,
        category: FailureCategory,
        severity: FailureSeverity,
        is_retryable: bool,
        requires_review: bool,
        artifact_ids: tuple[str, ...] = (),
    ) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=_STAGE,
            category=category,
            severity=severity,
            source=FailureSource.SYSTEM,
            message=message,
            is_retryable=is_retryable,
            requires_review=requires_review,
            artifact_ids=artifact_ids,
        )
        job.context.failures.add(failure)
        _log.error("job %r: [%s] %s", job.job_id, category, message)
