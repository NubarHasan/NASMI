from __future__ import annotations

import logging

from core.guards import require
from pipeline.artifact import (
    ArtifactType,
    EntityResolutionArtifact,
    KnowledgeBuildArtifact,
)
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult
from processing.extraction.candidate_fact import CandidateFact
from processing.knowledge_build.knowledge_build_result import KnowledgeBuildResult
from processing.knowledge_build.knowledge_build_service import KnowledgeBuildService

_log = logging.getLogger(__name__)

_STAGE = "knowledge_build"


class KnowledgeBuildHandler:

    def __init__(self, knowledge_build_service: KnowledgeBuildService) -> None:
        require(
            isinstance(knowledge_build_service, KnowledgeBuildService),
            "knowledge_build_service must be a KnowledgeBuildService",
        )
        self._service = knowledge_build_service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        resolution_artifact = self._resolve_resolution_artifact(job)
        if resolution_artifact is None:
            return

        entity_resolution_result = self._deserialise_resolution_result(
            job, resolution_artifact
        )
        if entity_resolution_result is None:
            return

        candidate_facts = self._deserialise_candidate_facts(job, resolution_artifact)
        if candidate_facts is None:
            return

        result = self._run_build(job, entity_resolution_result, candidate_facts)
        if result is None:
            return

        self._emit_artifact(job, resolution_artifact, result)

    def _resolve_resolution_artifact(
        self,
        job: Job,
    ) -> EntityResolutionArtifact | None:
        candidates = job.context.artifacts.by_type(ArtifactType.ENTITY_RESOLUTION)

        if not candidates:
            self._record_failure(
                job,
                message="no EntityResolutionArtifact found in context",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=False,
            )
            return None

        artifact = candidates[-1]

        if not isinstance(artifact, EntityResolutionArtifact):
            self._record_failure(
                job,
                message=(
                    f"artifact {artifact.artifact_id!r} has unexpected type "
                    f"{type(artifact).__name__!r} — expected EntityResolutionArtifact"
                ),
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

        return artifact

    def _deserialise_resolution_result(
        self,
        job: Job,
        artifact: EntityResolutionArtifact,
    ) -> EntityResolutionResult | None:
        snapshot = artifact.snapshot

        if not isinstance(snapshot, dict):
            self._record_failure(
                job,
                message=(
                    f"EntityResolutionArtifact {artifact.artifact_id!r} "
                    f"snapshot is not a dict"
                ),
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

        try:
            return EntityResolutionResult.from_dict(snapshot)
        except Exception as exc:
            _log.exception(
                "job %r: failed to deserialise EntityResolutionResult from artifact %r",
                job.job_id,
                artifact.artifact_id,
            )
            self._record_failure(
                job,
                message=f"EntityResolutionResult deserialisation failed: {exc}",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

    def _deserialise_candidate_facts(
        self,
        job: Job,
        artifact: EntityResolutionArtifact,
    ) -> tuple[CandidateFact, ...] | None:
        raw_facts = artifact.snapshot.get("candidate_facts")

        if not isinstance(raw_facts, list):
            self._record_failure(
                job,
                message=(
                    f"EntityResolutionArtifact {artifact.artifact_id!r} "
                    f"snapshot missing or invalid 'candidate_facts'"
                ),
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=True,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

        facts: list[CandidateFact] = []
        for item in raw_facts:
            try:
                facts.append(CandidateFact.from_dict(item))
            except Exception as exc:
                _log.exception(
                    "job %r: failed to deserialise CandidateFact from artifact %r",
                    job.job_id,
                    artifact.artifact_id,
                )
                self._record_failure(
                    job,
                    message=f"CandidateFact deserialisation failed: {exc}",
                    category=FailureCategory.VALIDATION,
                    severity=FailureSeverity.ERROR,
                    is_retryable=False,
                    requires_review=True,
                    artifact_ids=(artifact.artifact_id,),
                )
                return None

        if not facts:
            self._record_failure(
                job,
                message=(
                    f"EntityResolutionArtifact {artifact.artifact_id!r} "
                    f"contains no CandidateFacts"
                ),
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.WARNING,
                is_retryable=False,
                requires_review=False,
                artifact_ids=(artifact.artifact_id,),
            )
            return None

        return tuple(facts)

    def _run_build(
        self,
        job: Job,
        entity_resolution_result: EntityResolutionResult,
        candidate_facts: tuple[CandidateFact, ...],
    ) -> KnowledgeBuildResult | None:
        try:
            return self._service.process(
                entity_resolution_result=entity_resolution_result,
                candidate_facts=candidate_facts,
            )
        except Exception as exc:
            _log.exception(
                "job %r: KnowledgeBuildService raised unexpectedly", job.job_id
            )
            self._record_failure(
                job,
                message=f"KnowledgeBuildService raised: {exc}",
                category=FailureCategory.KNOWLEDGE_BUILD,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                requires_review=True,
            )
            return None

    def _emit_artifact(
        self,
        job: Job,
        resolution_artifact: EntityResolutionArtifact,
        result: KnowledgeBuildResult,
    ) -> None:
        artifact = KnowledgeBuildArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            entity_id=result.entity_id,
            fact_count=len(result.facts),
            evidence_count=len(result.evidence),
            conflict_count=len(result.conflicts),
            snapshot=result.to_dict(),
            source_artifact_ids=(resolution_artifact.artifact_id,),
        )
        job.context.artifacts.add(artifact)
        _log.info(
            "job %r: KnowledgeBuildArtifact emitted — "
            "entity=%r facts=%d evidence=%d conflicts=%d",
            job.job_id,
            artifact.entity_id,
            artifact.fact_count,
            artifact.evidence_count,
            artifact.conflict_count,
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
            source=FailureSource.SYSTEM,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=requires_review,
            artifact_ids=artifact_ids,
        )
        job.context.failures.add(failure)
        _log.error("job %r: [%s] %s", job.job_id, category.value, message)
