from __future__ import annotations

import logging
from typing import cast

from core.guards import require
from core.types import EntityId
from pipeline.artifact import (
    ArtifactType,
    FactAcceptanceArtifact,
    ProfileArtifact,
)
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.profile_build.profile_build_result import ProfileBuildResult
from processing.profile_build.profile_build_service import ProfileBuildService

_log = logging.getLogger(__name__)

_STAGE = "profile_build"


class ProfileBuildHandler:

    def __init__(self, profile_build_service: ProfileBuildService) -> None:
        require(
            isinstance(profile_build_service, ProfileBuildService),
            "profile_build_service must be a ProfileBuildService",
        )
        self._service = profile_build_service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")

        job.advance_stage(_STAGE)

        fa_artifacts = [
            a
            for a in job.context.artifacts.by_type(ArtifactType.FACT_ACCEPTANCE)
            if isinstance(a, FactAcceptanceArtifact)
        ]

        if not fa_artifacts:
            job.context.failures.add(
                _failure(job.job_id, "no FactAcceptanceArtifact found in bundle")
            )
            return

        fa = fa_artifacts[-1]
        entity_id = cast(EntityId, fa.entity_id)

        entity = job.knowledge_service.get_entity(entity_id)
        if entity is None:
            job.context.failures.add(
                _failure(
                    job.job_id, f"entity {entity_id!r} not found in KnowledgeService"
                )
            )
            return

        try:
            result: ProfileBuildResult = self._service.build(
                entity_id=entity.entity_id,
                entity_type=entity.entity_type,
                display_name=entity.display_name,
            )
        except Exception as exc:
            _log.exception("ProfileBuildService.build failed for entity %r", entity_id)
            job.context.failures.add(_failure(job.job_id, str(exc)))
            return

        snapshot = {
            "entity_id": result.entity_id,
            "entity_type": entity.entity_type,
            "fields_built": result.fields_built,
            "fields_missing": list(result.fields_missing),
            "completeness": result.completeness,
            "skipped_facts": result.skipped_facts,
            "is_complete": result.is_complete,
        }

        artifact = ProfileArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            entity_id=result.entity_id,
            snapshot=snapshot,
            source_artifact_ids=(fa.artifact_id,),
        )

        job.context.artifacts.add(artifact)
        job.set_profile(result.profile)

        _log.info(
            "profile built for entity %r — completeness=%.2f fields=%d missing=%d",
            entity_id,
            result.completeness,
            result.fields_built,
            len(result.fields_missing),
        )


def _failure(job_id: str, message: str) -> PipelineFailure:
    return PipelineFailure.create(
        job_id=job_id,
        stage=_STAGE,
        category=FailureCategory.SYSTEM,
        severity=FailureSeverity.ERROR,
        source=FailureSource.SYSTEM,
        message=message,
        is_retryable=False,
        requires_review=True,
    )
