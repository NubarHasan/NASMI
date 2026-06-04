from __future__ import annotations

import logging

from processing.candidate_fact import CandidateFact

from core.guards import require
from core.types import EntityId
from pipeline.artifact import ArtifactType, EntityResolutionArtifact, ExtractionArtifact
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult
from processing.entity_resolution.entity_resolution_service import (
    EntityResolutionService,
)

_log = logging.getLogger(__name__)

_STAGE = "entity_resolution"


class EntityResolutionHandler:

    def __init__(self, resolution_service: EntityResolutionService) -> None:
        require(
            isinstance(resolution_service, EntityResolutionService),
            "resolution_service must be an EntityResolutionService",
        )
        self._service = resolution_service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        job.advance_stage(_STAGE)

        extraction_artifacts = self._resolve_extraction_artifacts(job)
        if extraction_artifacts is None:
            return

        candidate_facts = self._build_candidate_facts(job, extraction_artifacts)
        if candidate_facts is None:
            return

        entity_id = self._resolve_entity_id(job, candidate_facts)
        if entity_id is None:
            return

        result = self._run_resolution(job, entity_id, candidate_facts)
        if result is None:
            return

        self._emit_artifact(job, extraction_artifacts, result)

    def _resolve_extraction_artifacts(
        self,
        job: Job,
    ) -> list[ExtractionArtifact] | None:
        candidates = job.context.artifacts.by_type(ArtifactType.EXTRACTION)

        if not candidates:
            self._record_failure(
                job,
                message="no ExtractionArtifact found in context",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.ERROR,
                is_retryable=False,
                requires_review=False,
            )
            return None

        typed: list[ExtractionArtifact] = []
        for artifact in candidates:
            if not isinstance(artifact, ExtractionArtifact):
                self._record_failure(
                    job,
                    message=(
                        f"artifact {artifact.artifact_id!r} has unexpected type "
                        f"{type(artifact).__name__!r} — expected ExtractionArtifact"
                    ),
                    category=FailureCategory.VALIDATION,
                    severity=FailureSeverity.ERROR,
                    is_retryable=False,
                    requires_review=True,
                    artifact_ids=(artifact.artifact_id,),
                )
                return None
            typed.append(artifact)

        return typed

    def _build_candidate_facts(
        self,
        job: Job,
        extraction_artifacts: list[ExtractionArtifact],
    ) -> list[CandidateFact] | None:
        facts: list[CandidateFact] = []

        for artifact in extraction_artifacts:
            raw_facts = artifact.snapshot.get("candidate_facts")

            if not isinstance(raw_facts, list):
                self._record_failure(
                    job,
                    message=(
                        f"ExtractionArtifact {artifact.artifact_id!r} "
                        f"snapshot missing or invalid 'candidate_facts'"
                    ),
                    category=FailureCategory.VALIDATION,
                    severity=FailureSeverity.ERROR,
                    is_retryable=False,
                    requires_review=True,
                    artifact_ids=(artifact.artifact_id,),
                )
                return None

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
                message="no CandidateFacts found across all ExtractionArtifacts",
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.WARNING,
                is_retryable=False,
                requires_review=False,
            )
            return None

        return facts

    def _resolve_entity_id(
        self,
        job: Job,
        candidate_facts: list[CandidateFact],
    ) -> EntityId | None:
        entity_ids: set[str] = {str(f.entity_id) for f in candidate_facts}

        if len(entity_ids) > 1:
            self._record_failure(
                job,
                message=(
                    f"CandidateFacts span multiple entities: {sorted(entity_ids)!r} "
                    f"— cannot resolve across entity boundaries"
                ),
                category=FailureCategory.VALIDATION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                requires_review=True,
            )
            return None

        return EntityId(entity_ids.pop())

    def _run_resolution(
        self,
        job: Job,
        entity_id: EntityId,
        candidate_facts: list[CandidateFact],
    ) -> EntityResolutionResult | None:
        try:
            return self._service.resolve(
                facts=candidate_facts,
                entity_id=entity_id,
            )
        except Exception as exc:
            _log.exception(
                "job %r: EntityResolutionService raised unexpectedly", job.job_id
            )
            self._record_failure(
                job,
                message=f"EntityResolutionService raised: {exc}",
                category=FailureCategory.ENTITY_RESOLUTION,
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                requires_review=True,
            )
            return None

    def _emit_artifact(
        self,
        job: Job,
        extraction_artifacts: list[ExtractionArtifact],
        result: EntityResolutionResult,
    ) -> None:
        artifact = EntityResolutionArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            entity_id=result.resolved_entity_id,
            fact_count=result.fact_count,
            resolution_confidence=result.resolution_confidence,
            has_conflicts=result.has_conflicts,
            snapshot=result.to_dict(),
            source_artifact_ids=tuple(a.artifact_id for a in extraction_artifacts),
        )
        job.context.artifacts.add(artifact)
        _log.info(
            "job %r: EntityResolutionArtifact emitted — "
            "entity=%r facts=%d confidence=%.4f has_conflicts=%s",
            job.job_id,
            artifact.entity_id,
            artifact.fact_count,
            artifact.resolution_confidence,
            artifact.has_conflicts,
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
