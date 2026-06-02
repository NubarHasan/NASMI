from __future__ import annotations

import logging

from archive.document import Document
from core.guards import require
from pipeline.artifact import DocumentArtifact
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job

_log = logging.getLogger(__name__)

_STAGE = "document_import"


class DocumentImportHandler:

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        document = self._load_document(job)
        if document is None:
            return

        self._emit_artifact(job, document)

    def _load_document(self, job: Job) -> Document | None:
        payload = job.get_payload()
        raw = payload.get("document")

        if not isinstance(raw, dict) or not raw:
            _log.error("job %r: missing or invalid 'document' in payload", job.job_id)
            self._record_failure(
                job,
                message="payload missing required key 'document'",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={"error_code": "MISSING_DOCUMENT_PAYLOAD"},
            )
            return None

        try:
            return Document.from_dict(raw)
        except Exception as exc:
            _log.error("job %r: failed to deserialise Document: %s", job.job_id, exc)
            self._record_failure(
                job,
                message=f"Document deserialisation failed: {exc}",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={
                    "error_code": "DOCUMENT_DESERIALISE_ERROR",
                    "exception_type": type(exc).__name__,
                },
            )
            return None

    def _emit_artifact(self, job: Job, document: Document) -> None:
        artifact = DocumentArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            document_id=document.document_id,
            snapshot=document.to_dict(),
        )
        job.context.artifacts.add(artifact)
        _log.info(
            "job %r: DocumentArtifact %r created for document %r",
            job.job_id,
            artifact.artifact_id,
            document.document_id,
        )

    @staticmethod
    def _record_failure(
        job: Job,
        message: str,
        category: FailureCategory,
        severity: FailureSeverity,
        is_retryable: bool,
        metadata: dict | None = None,
    ) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=_STAGE,
            category=category,
            source=FailureSource.HANDLER,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=True,
            metadata=metadata or {},
        )
        job.context.failures.add(failure)
