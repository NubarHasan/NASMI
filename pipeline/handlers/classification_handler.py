from __future__ import annotations

import logging
from typing import Any

from core.guards import require
from pipeline.artifact import ArtifactType, DocumentArtifact, OcrArtifact
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job

_log = logging.getLogger(__name__)

_STAGE = "classification"

_KEYWORDS: list[tuple[str, list[str]]] = [
    ("passport", ["passport", "travel document", "passeport"]),
    (
        "id_card",
        ["national id", "identity card", "personalausweis", "carte d'identité"],
    ),
    (
        "residence_permit",
        ["residence permit", "aufenthaltstitel", "aufenthaltserlaubnis"],
    ),
    ("bank_statement", ["bank statement", "account statement", "kontoauszug"]),
    ("contract", ["contract", "agreement", "vertrag"]),
    ("invoice", ["invoice", "rechnung", "facture"]),
    ("certificate", ["certificate", "zertifikat", "certificat"]),
]

_DEFAULT_DOC_TYPE = "passport"


def _classify_from_text(text: str) -> str:
    lowered = text.lower()
    for doc_type, keywords in _KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return doc_type
    return _DEFAULT_DOC_TYPE


class ClassificationHandler:

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        ocr_artifact = self._resolve_ocr_artifact(job)
        if ocr_artifact is None:
            return

        doc_artifact = self._resolve_document_artifact(job, ocr_artifact)
        if doc_artifact is None:
            return

        current_doc_type: str | None = doc_artifact.snapshot.get("doc_type")

        if current_doc_type and current_doc_type not in ("unknown", ""):
            _log.info(
                "job %r: doc_type already set to %r — skipping classification",
                job.job_id,
                current_doc_type,
            )
            return

        full_text: str = ocr_artifact.snapshot.get("full_text", "")
        detected_type = _classify_from_text(full_text)

        updated_snapshot = dict(doc_artifact.snapshot)
        updated_snapshot["doc_type"] = detected_type

        updated_artifact = DocumentArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            document_id=doc_artifact.document_id,
            snapshot=updated_snapshot,
            source_artifact_ids=(doc_artifact.artifact_id,),
        )
        job.context.artifacts.add(updated_artifact)

        _log.info(
            "job %r: classified document %r as %r",
            job.job_id,
            doc_artifact.document_id,
            detected_type,
        )

    def _resolve_ocr_artifact(self, job: Job) -> OcrArtifact | None:
        candidates = job.context.artifacts.by_type(ArtifactType.OCR)
        if not candidates:
            self._record_failure(
                job,
                message="no OcrArtifact in context",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
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
            )
            return None
        return artifact

    def _resolve_document_artifact(
        self, job: Job, ocr_artifact: OcrArtifact
    ) -> DocumentArtifact | None:
        for artifact_id in ocr_artifact.source_artifact_ids:
            artifact = job.context.artifacts.get(artifact_id)
            if isinstance(artifact, DocumentArtifact):
                return artifact
        candidates = job.context.artifacts.by_type(ArtifactType.DOCUMENT)
        if candidates:
            artifact = candidates[-1]
            if isinstance(artifact, DocumentArtifact):
                return artifact
        self._record_failure(
            job,
            message="no DocumentArtifact found in context",
            category=FailureCategory.VALIDATION,
            severity=FailureSeverity.ERROR,
            is_retryable=False,
        )
        return None

    @staticmethod
    def _record_failure(
        job: Job,
        message: str,
        category: FailureCategory,
        severity: FailureSeverity,
        is_retryable: bool,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=_STAGE,
            category=category,
            source=FailureSource.SYSTEM,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=False,
            metadata=metadata or {},
        )
        job.context.failures.add(failure)
