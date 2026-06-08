from __future__ import annotations

import logging
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_candidate_fact_id,
    generate_evidence_id,
    is_valid_candidate_fact_id,
    is_valid_evidence_id,
)
from core.types import (
    CandidateFactId,
    DocumentId,
    EntityId,
    EvidenceId,
    LanguageCode,
    SourceId,
)
from infrastructure.db.repositories.sqlite_noise_repository import SqliteNoiseRepository
from infrastructure.db.repositories.sqlite_review_repository import (
    SqliteReviewRepository,
)
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
from review.review_case import ReviewCase
from review.review_type import ReviewPriority

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

        if self._has_candidate_facts(result):
            self._persist_review_cases(job, doc_artifact, result)
            return

        self._persist_deferred_llm_noise(job, ocr_artifact, doc_artifact, result)

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

    def _has_candidate_facts(self, result: ExtractionResult) -> bool:
        return bool(self._get_candidate_facts(result))

    def _get_candidate_facts(self, result: ExtractionResult) -> list[Any]:
        candidates = getattr(result, "candidate_facts", None)
        if candidates:
            return list(candidates)

        data = result.to_dict()
        values = (
            data.get("candidate_facts")
            or data.get("candidates")
            or data.get("facts")
            or []
        )

        return list(values)

    def _persist_review_cases(
        self,
        job: Job,
        doc_artifact: DocumentArtifact,
        result: ExtractionResult,
    ) -> None:
        try:
            db = _resolve_db_connection()
            if db is None:
                _log.warning(
                    "job %r: review case persistence skipped, db unavailable",
                    job.job_id,
                )
                return

            repo = SqliteReviewRepository(db)
            doc_snapshot = doc_artifact.snapshot
            entity_id = str(doc_snapshot.get("entity_id") or "").strip()
            candidates = self._get_candidate_facts(result)

            if not entity_id or not candidates:
                return

            created = 0

            for candidate in candidates:
                fact_type = self._candidate_value(
                    candidate,
                    "fact_type",
                    "field_name",
                    "type",
                )
                raw_value = self._candidate_value(
                    candidate,
                    "raw_value",
                    "raw",
                    "value",
                    "display_value",
                )
                normalized_value = self._candidate_value(
                    candidate,
                    "normalized_value",
                    "normalized",
                    "canonical_value",
                    "value",
                )
                confidence = self._candidate_float(
                    candidate,
                    "confidence",
                    default=float(result.mean_confidence or 0.0),
                )

                if not str(raw_value or normalized_value or fact_type).strip():
                    continue

                candidate_fact_id = self._candidate_fact_id(candidate)
                evidence_ids = self._candidate_evidence_ids(candidate)

                case = ReviewCase.create(
                    entity_id=EntityId(entity_id),
                    candidate_fact_id=candidate_fact_id,
                    fact_type=str(fact_type or "review_candidate"),
                    raw_value=str(raw_value or normalized_value or ""),
                    normalized_value=str(normalized_value or raw_value or ""),
                    confidence=float(max(0.0, min(1.0, confidence))),
                    evidence_ids=evidence_ids,
                    priority=self._priority_for_confidence(confidence),
                    metadata={
                        "job_id": job.job_id,
                        "source": "extraction_handler",
                        "document_id": str(result.document_id),
                        "source_id": str(result.source_id),
                        "extractor_id": str(result.extractor_id),
                        "llm_cleanup_pending": bool(
                            result.metadata.get("llm_cleanup_pending")
                        ),
                        "extraction_metadata": dict(result.metadata),
                    },
                )

                repo.save(case)
                created += 1

            _log.info(
                "job %r: persisted %d extraction candidates to review_cases",
                job.job_id,
                created,
            )

        except Exception as exc:
            _log.exception("job %r: failed to persist review cases", job.job_id)
            self._record_failure(
                job,
                message=f"failed to persist review cases: {exc}",
                category=FailureCategory.EXTRACTION,
                severity=FailureSeverity.WARNING,
                is_retryable=False,
                requires_review=False,
            )

    def _candidate_value(self, candidate: Any, *keys: str) -> str:
        for key in keys:
            value = None

            if isinstance(candidate, dict):
                value = candidate.get(key)
            else:
                value = getattr(candidate, key, None)

            if value is not None and str(value).strip():
                return str(value).strip()

        return ""

    def _candidate_float(
        self,
        candidate: Any,
        key: str,
        default: float = 0.0,
    ) -> float:
        value = None

        value = (
            candidate.get(key)
            if isinstance(candidate, dict)
            else getattr(candidate, key, None)
        )

        try:
            return float(value)
        except Exception:
            return float(default)

    def _candidate_fact_id(self, candidate: Any) -> CandidateFactId:
        value = self._candidate_value(
            candidate,
            "candidate_fact_id",
            "fact_id",
            "id",
        )

        if value and is_valid_candidate_fact_id(value):
            return CandidateFactId(value)

        return generate_candidate_fact_id()

    def _candidate_evidence_ids(self, candidate: Any) -> tuple[EvidenceId, ...]:
        value = None

        if isinstance(candidate, dict):
            value = candidate.get("evidence_ids")
        else:
            value = getattr(candidate, "evidence_ids", None)

        valid_ids: list[EvidenceId] = []

        if isinstance(value, str):
            if value.strip() and is_valid_evidence_id(value.strip()):
                valid_ids.append(EvidenceId(value.strip()))
        elif value is not None:
            try:
                for item in value:
                    text = str(item).strip()
                    if text and is_valid_evidence_id(text):
                        valid_ids.append(EvidenceId(text))
            except Exception:
                pass

        if valid_ids:
            return tuple(valid_ids)

        return (generate_evidence_id(),)

    def _priority_for_confidence(self, confidence: float) -> ReviewPriority:
        if confidence < 0.6 and hasattr(ReviewPriority, "HIGH"):
            return ReviewPriority.HIGH

        if confidence < 0.8 and hasattr(ReviewPriority, "NORMAL"):
            return ReviewPriority.NORMAL

        if hasattr(ReviewPriority, "LOW"):
            return ReviewPriority.LOW

        values = list(ReviewPriority)
        if not values:
            raise ValueError("ReviewPriority enum has no values")
        return values[0]

    def _persist_deferred_llm_noise(
        self,
        job: Job,
        ocr_artifact: OcrArtifact,
        doc_artifact: DocumentArtifact,
        result: ExtractionResult,
    ) -> None:
        try:
            if not bool(result.metadata.get("llm_cleanup_pending")):
                return

            ocr_snapshot = ocr_artifact.snapshot
            doc_snapshot = doc_artifact.snapshot

            raw_text = str(ocr_snapshot.get("full_text") or "").strip()
            if not raw_text:
                return

            entity_id = str(doc_snapshot.get("entity_id") or "").strip() or None
            document_id = str(result.document_id)
            source_id = str(result.source_id)

            db = _resolve_db_connection()
            if db is None:
                _log.warning(
                    "job %r: noise persistence skipped, db unavailable",
                    job.job_id,
                )
                return

            _ensure_noise_schema_supports_statuses(db)

            if _noise_exists(
                db=db,
                entity_id=entity_id,
                document_id=document_id,
                source_id=source_id,
                stage="llm_cleanup",
            ):
                return

            repo = SqliteNoiseRepository(db)
            repo.create(
                raw_text=raw_text,
                reason=str(
                    result.metadata.get("llm_cleanup_reason")
                    or "OCR extraction needs deferred LLM cleanup"
                ),
                stage="llm_cleanup",
                entity_id=entity_id,
                document_id=document_id,
                source_id=source_id,
                confidence=float(result.mean_confidence or 0.0),
                metadata={
                    "job_id": job.job_id,
                    "source": "extraction_handler",
                    "review_source": "ocr",
                    "llm_cleanup_pending": True,
                    "extractor_id": str(result.extractor_id),
                    "candidate_count": result.candidate_count,
                    "mean_confidence": result.mean_confidence,
                    "document_type": doc_snapshot.get("doc_type"),
                    "language": doc_snapshot.get("language"),
                    "extraction_metadata": dict(result.metadata),
                },
            )

            _log.info(
                "job %r: deferred LLM noise item created for document=%s",
                job.job_id,
                document_id,
            )

        except Exception as exc:
            _log.exception("job %r: failed to persist deferred LLM noise", job.job_id)
            self._record_failure(
                job,
                message=f"failed to persist deferred LLM noise: {exc}",
                category=FailureCategory.EXTRACTION,
                severity=FailureSeverity.WARNING,
                is_retryable=False,
                requires_review=False,
                artifact_ids=(ocr_artifact.artifact_id,),
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


def _resolve_db_connection() -> Any | None:
    try:
        from ui.services.api_client import _get_db

        return _get_db()
    except Exception:
        return None


def _noise_exists(
    db: Any,
    entity_id: str | None,
    document_id: str,
    source_id: str,
    stage: str,
) -> bool:
    row = db.connection.execute(
        """
        SELECT 1
        FROM noise_items
        WHERE COALESCE(entity_id, '') = COALESCE(?, '')
          AND COALESCE(document_id, '') = COALESCE(?, '')
          AND COALESCE(source_id, '') = COALESCE(?, '')
          AND stage = ?
          AND status IN ('open', 'processing', 'promoted', 'reviewed', 'failed')
        LIMIT 1
        """,
        (entity_id, document_id, source_id, stage),
    ).fetchone()

    return row is not None


def _ensure_noise_schema_supports_statuses(db: Any) -> None:
    row = db.connection.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'noise_items'
        """).fetchone()

    if row is None:
        return

    sql = str(row["sql"] if hasattr(row, "keys") else row[0])

    if "processing" in sql and "failed" in sql:
        return

    db.connection.execute("ALTER TABLE noise_items RENAME TO noise_items_old")

    db.connection.execute("""
        CREATE TABLE noise_items (
            noise_id TEXT PRIMARY KEY,
            entity_id TEXT,
            document_id TEXT,
            source_id TEXT,
            stage TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            reason TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.0 CHECK (
                confidence >= 0.0
                AND confidence <= 1.0
            ),
            status TEXT NOT NULL CHECK (
                status IN ('open', 'processing', 'reviewed', 'ignored', 'promoted', 'failed')
            ),
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            metadata TEXT NOT NULL DEFAULT '{}'
        )
        """)

    db.connection.execute("""
        INSERT INTO noise_items (
            noise_id,
            entity_id,
            document_id,
            source_id,
            stage,
            raw_text,
            reason,
            confidence,
            status,
            created_at,
            reviewed_at,
            metadata
        )
        SELECT
            noise_id,
            entity_id,
            document_id,
            source_id,
            stage,
            raw_text,
            reason,
            confidence,
            status,
            created_at,
            reviewed_at,
            metadata
        FROM noise_items_old
        """)

    db.connection.execute("DROP TABLE noise_items_old")
    db.connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_noise_items_entity_id ON noise_items(entity_id)"
    )
    db.connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_noise_items_document_id ON noise_items(document_id)"
    )
    db.connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_noise_items_status ON noise_items(status)"
    )
    db.connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_noise_items_stage ON noise_items(stage)"
    )
    db.connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_noise_items_created_at ON noise_items(created_at)"
    )
    db.connection.commit()
