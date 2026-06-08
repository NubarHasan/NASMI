from __future__ import annotations

import logging
from pathlib import Path

from archive.document import Document
from archive.source import Source
from core.guards import require
from infrastructure.db.connection import get_db
from infrastructure.db.repositories.sqlite_source_repository import (
    SqliteSourceRepository,
)
from pipeline.artifact import ArtifactType, DocumentArtifact, OcrArtifact
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.ocr.ocr_request import OcrRequest
from processing.ocr.ocr_result import OcrResult
from processing.ocr.ocr_service import OcrService

_log = logging.getLogger(__name__)

_STAGE = "ocr"


class OcrHandler:

    def __init__(self, ocr_service: OcrService) -> None:
        require(
            isinstance(ocr_service, OcrService),
            "ocr_service must be an OcrService",
        )
        self._ocr_service = ocr_service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        doc_artifact = self._resolve_document_artifact(job)
        if doc_artifact is None:
            return

        document = self._load_document(job, doc_artifact)
        if document is None:
            return

        source = Source.from_document(
            entity_id=document.entity_id,
            document=document,
        )

        if not self._persist_source(job, source):
            return

        request = self._build_request(job, document, source)
        if request is None:
            return

        result = self._run_ocr(job, request)
        if result is None:
            return

        self._emit_artifact(job, doc_artifact, document, source, result)

    def _resolve_document_artifact(self, job: Job) -> DocumentArtifact | None:
        candidates = job.context.artifacts.by_type(ArtifactType.DOCUMENT)

        if not candidates:
            self._record_failure(
                job=job,
                message="no DocumentArtifact in context",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={"error_code": "MISSING_DOCUMENT_ARTIFACT"},
            )
            return None

        artifact = candidates[-1]

        if not isinstance(artifact, DocumentArtifact):
            self._record_failure(
                job=job,
                message="artifact type mismatch — expected DocumentArtifact",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={"error_code": "ARTIFACT_TYPE_MISMATCH"},
            )
            return None

        return artifact

    def _load_document(self, job: Job, artifact: DocumentArtifact) -> Document | None:
        try:
            return Document.from_dict(artifact.snapshot)
        except Exception as exc:
            self._record_failure(
                job=job,
                message=f"Document reconstruction failed: {exc}",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={
                    "error_code": "DOCUMENT_RECONSTRUCT_ERROR",
                    "exception_type": type(exc).__name__,
                },
            )
            return None

    def _persist_source(self, job: Job, source: Source) -> bool:
        try:
            db = get_db()
            repo = SqliteSourceRepository(db)
            repo.save(source)
            db.connection.commit()

            _log.info(
                "job %r: Source %r persisted for document %r",
                job.job_id,
                source.source_id,
                source.document_id,
            )
            return True

        except Exception as exc:
            self._record_failure(
                job=job,
                message=f"Source persistence failed: {exc}",
                category=FailureCategory.SYSTEM,
                severity=FailureSeverity.CRITICAL,
                is_retryable=True,
                metadata={
                    "error_code": "SOURCE_PERSIST_ERROR",
                    "exception_type": type(exc).__name__,
                    "source_id": str(getattr(source, "source_id", "")),
                    "document_id": str(getattr(source, "document_id", "")),
                },
            )
            return False

    def _build_request(
        self,
        job: Job,
        document: Document,
        source: Source,
    ) -> OcrRequest | None:
        try:
            return OcrRequest.from_file(
                source_id=source.source_id,
                file_path=Path(document.file_path),
                languages=(document.language,),
            )
        except Exception as exc:
            self._record_failure(
                job=job,
                message=f"OcrRequest construction failed: {exc}",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={
                    "error_code": "OCR_REQUEST_BUILD_ERROR",
                    "exception_type": type(exc).__name__,
                },
            )
            return None

    def _run_ocr(self, job: Job, request: OcrRequest) -> OcrResult | None:
        engine_name: str | None = job.get_payload().get("engine_name")

        try:
            return self._ocr_service.process(request, engine_name=engine_name)
        except Exception as exc:
            self._record_failure(
                job=job,
                message=f"OCR engine failed: {exc}",
                category=FailureCategory.SYSTEM,
                severity=FailureSeverity.CRITICAL,
                is_retryable=True,
                metadata={
                    "error_code": "OCR_ENGINE_ERROR",
                    "exception_type": type(exc).__name__,
                    "engine_name": engine_name,
                },
            )
            return None

    def _emit_artifact(
        self,
        job: Job,
        doc_artifact: DocumentArtifact,
        document: Document,
        source: Source,
        result: OcrResult,
    ) -> None:
        artifact = OcrArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            document_id=document.document_id,
            source_id=source.source_id,
            page_count=result.page_count,
            mean_confidence=result.mean_confidence,
            snapshot=result.to_dict(),
            source_artifact_ids=(doc_artifact.artifact_id,),
        )

        job.context.artifacts.add(artifact)

        _log.info(
            "job %r: OcrArtifact %r created — pages=%d confidence=%.4f",
            job.job_id,
            artifact.artifact_id,
            artifact.page_count,
            artifact.mean_confidence,
        )

    @staticmethod
    def _record_failure(
        job: Job,
        message: str,
        category: FailureCategory,
        severity: FailureSeverity,
        is_retryable: bool,
        metadata: dict[str, object] | None = None,
    ) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=_STAGE,
            category=category,
            source=FailureSource.SYSTEM,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=True,
            metadata=metadata or {},
        )
        job.context.failures.add(failure)
