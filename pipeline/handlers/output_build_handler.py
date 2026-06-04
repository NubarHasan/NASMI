from __future__ import annotations

import logging
from typing import cast

from core.guards import require
from core.types import EntityId
from output.output_format import OutputFormat
from output.output_type import OutputType
from pipeline.artifact import (
    ArtifactType,
    OutputArtifact,
    ProfileArtifact,
)
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from processing.output_build.output_build_service import (
    OutputBuildResult,
    OutputBuildService,
)

_log = logging.getLogger(__name__)

_STAGE = "output_build"

_DEFAULT_OUTPUT_TYPES: tuple[OutputType, ...] = (
    OutputType.PROFILE_REPORT,
    OutputType.FACT_EXPORT,
    OutputType.KNOWLEDGE_REPORT,
)


class OutputBuildHandler:

    def __init__(
        self,
        output_build_service: OutputBuildService,
        output_types: tuple[OutputType, ...] = _DEFAULT_OUTPUT_TYPES,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> None:
        require(
            isinstance(output_build_service, OutputBuildService),
            "output_build_service must be an OutputBuildService",
        )
        require(len(output_types) > 0, "output_types must not be empty")
        require(
            isinstance(output_format, OutputFormat),
            "output_format must be an OutputFormat",
        )
        self._service = output_build_service
        self._output_types = output_types
        self._output_format = output_format

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")

        job.advance_stage(_STAGE)

        profile_artifacts = [
            a
            for a in job.context.artifacts.by_type(ArtifactType.PROFILE)
            if isinstance(a, ProfileArtifact)
        ]

        if not profile_artifacts:
            job.context.failures.add(
                _make_failure(job.job_id, "no ProfileArtifact found in bundle")
            )
            return

        pa = profile_artifacts[-1]
        entity_id = cast(EntityId, pa.entity_id)

        try:
            result: OutputBuildResult = self._service.build(
                entity_id=entity_id,
                output_types=self._output_types,
                output_format=self._output_format,
            )
        except Exception as exc:
            _log.exception("OutputBuildService.build raised for entity %r", entity_id)
            job.context.failures.add(_make_failure(job.job_id, str(exc)))
            return

        if result.succeeded_count == 0:
            job.context.failures.add(
                _make_failure(
                    job.job_id,
                    f"all {result.failed_count} output(s) failed "
                    f"for entity {entity_id!r}",
                )
            )
            return

        for doc in result.documents:
            artifact = OutputArtifact.create(
                job_id=job.job_id,
                stage=_STAGE,
                entity_id=str(entity_id),
                output_document_id=str(doc.output_document_id),
                output_type=doc.output_type,
                output_format=doc.output_format,
                file_path=str(doc.file_path),
                source_artifact_ids=(pa.artifact_id,),
            )
            job.context.artifacts.add(artifact)

        if result.failed_count > 0:
            _log.warning(
                "partial output failure for entity %r — " "succeeded=%d failed=%d",
                entity_id,
                result.succeeded_count,
                result.failed_count,
            )

        _log.info(
            "output_build complete entity=%r succeeded=%d failed=%d",
            entity_id,
            result.succeeded_count,
            result.failed_count,
        )


def _make_failure(job_id: str, message: str) -> PipelineFailure:
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
