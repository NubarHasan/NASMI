from __future__ import annotations

import logging

from core.guards import require
from core.types import EntityId
from pipeline.artifact import (
    ArtifactType,
    FactAcceptanceArtifact,
    KnowledgeBuildArtifact,
)
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.fact_acceptance.fact_acceptance_result import FactAcceptanceResult
from processing.fact_acceptance.fact_acceptance_service import FactAcceptanceService

_log = logging.getLogger(__name__)

_STAGE = "fact_acceptance"


class FactAcceptanceHandler:

    def __init__(self, fact_acceptance_service: FactAcceptanceService) -> None:
        require(
            isinstance(fact_acceptance_service, FactAcceptanceService),
            "fact_acceptance_service must be a FactAcceptanceService",
        )
        self._service = fact_acceptance_service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        kb_artifact = self._resolve_knowledge_build_artifact(job)
        if kb_artifact is None:
            return

        entity_id = self._extract_entity_id(job, kb_artifact)
        if entity_id is None:
            return

        result = self._run_acceptance(job, entity_id)
        if result is None:
            return

        self._emit_artifact(job, kb_artifact, result)

    def _resolve_knowledge_build_artifact(
        self, job: Job
    ) -> KnowledgeBuildArtifact | None:
        candidates = job.context.artifacts.by_type(ArtifactType.KNOWLEDGE_BUILD)

        if not candidates:
            self._record_failure(
                job,
                message="no KnowledgeBuildArtifact found in context",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=False,
            )
            return None

        artifact = candidates[-1]

        if not isinstance(artifact, KnowledgeBuildArtifact):
            self._record_failure(
                job,
                message=f"artifact {artifact.artifact_id!r} has unexpected type {type(artifact).__name__!r} — expected KnowledgeBuildArtifact",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

        return artifact

    def _extract_entity_id(
        self, job: Job, artifact: KnowledgeBuildArtifact
    ) -> EntityId | None:
        raw = artifact.entity_id

        if not isinstance(raw, str) or not raw.strip():
            self._record_failure(
                job,
                message=f"KnowledgeBuildArtifact {artifact.artifact_id!r} has missing or blank entity_id",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

        return EntityId(raw)

    def _run_acceptance(
        self, job: Job, entity_id: EntityId
    ) -> FactAcceptanceResult | None:
        try:
            return self._service.process(entity_id=entity_id)
        except Exception as exc:
            _log.exception(
                "job %r: FactAcceptanceService raised unexpectedly", job.job_id
            )
            self._record_failure(
                job,
                message=f"FactAcceptanceService raised: {exc}",
                category=FailureCategory.KNOWLEDGE,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                requires_review=True,
            )
            return None

    def _emit_artifact(
        self,
        job: Job,
        kb_artifact: KnowledgeBuildArtifact,
        result: FactAcceptanceResult,
    ) -> None:
        artifact = FactAcceptanceArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            entity_id=str(result.entity_id),
            accepted_count=len(result.accepted_facts),
            review_required_count=len(result.review_cases),
            conflict_count=len(result.conflicts),
            rejected_count=len(result.rejected_facts),
            snapshot=result.to_dict(),
            source_artifact_ids=(kb_artifact.artifact_id,),
        )
        job.context.artifacts.add(artifact)

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
            source=FailureSource.SYSTEM,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=requires_review,
            artifact_ids=artifact_ids,
        )
        job.context.failures.add(failure)
        _log.error("job %r: [%s] %s", job.job_id, category.value, message)
