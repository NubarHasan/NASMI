from __future__ import annotations

import logging

from core.guards import require
from core.types import EntityId
from output.output_format import OutputFormat
from output.output_type import OutputType
from pipeline.artifact import ArtifactType, OutputArtifact, ProfileArtifact
from pipeline.job import Job, JobStatus
from processing.output_build.output_build_service import OutputBuildService

_log = logging.getLogger(__name__)

_STAGE = "output_build"

_DEFAULT_OUTPUT_TYPES: tuple[OutputType, ...] = (
    OutputType.PROFILE_REPORT,
    OutputType.FACT_EXPORT,
    OutputType.KNOWLEDGE_REPORT,
    OutputType.CONFLICT_REPORT,
    OutputType.EVIDENCE_REPORT,
    OutputType.PROVENANCE_REPORT,
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
        require(
            len(output_types) > 0,
            "output_types must not be empty",
        )
        require(
            all(isinstance(t, OutputType) for t in output_types),
            "all output_types must be OutputType instances",
        )
        require(
            isinstance(output_format, OutputFormat),
            "output_format must be an OutputFormat",
        )
        self._service = output_build_service
        self._output_types = output_types
        self._output_format = output_format

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")

        job.start()
        job.advance_stage(_STAGE)

        profile_artifact = self._resolve_profile_artifact(job)
        if profile_artifact is None:
            job.fail()
            return

        # FIX 1: cast str → EntityId
        entity_id = EntityId(profile_artifact.entity_id)

        _log.info(
            "output_build started — job=%r entity=%r types=%r",
            job.job_id,
            entity_id,
            self._output_types,
        )

        result = self._service.build(
            entity_id=entity_id,
            output_types=self._output_types,
            output_format=self._output_format,
        )

        for doc in result.documents:
            artifact = OutputArtifact.create(
                job_id=job.job_id,
                stage=_STAGE,
                entity_id=entity_id,
                # FIX 2: document_id → output_document_id
                output_document_id=doc.output_document_id,
                output_type=doc.output_type,
                output_format=doc.output_format,
                # FIX 3: Path → str
                file_path=str(doc.file_path),
                source_artifact_ids=(profile_artifact.artifact_id,),
            )
            job.bundle.add(artifact)

        _log.info(
            "output_build finished — job=%r entity=%r succeeded=%d failed=%d",
            job.job_id,
            entity_id,
            result.succeeded_count,
            result.failed_count,
        )

        if result.is_complete:
            job.complete()
        else:
            job.fail()

    def _resolve_profile_artifact(self, job: Job) -> ProfileArtifact | None:
        artifacts = job.bundle.by_type(ArtifactType.PROFILE)
        if not artifacts:
            _log.error(
                "no ProfileArtifact found in bundle — job=%r",
                job.job_id,
            )
            return None
        artifact = artifacts[-1]
        if not isinstance(artifact, ProfileArtifact):
            _log.error(
                "expected ProfileArtifact, got %r — job=%r",
                type(artifact).__name__,
                job.job_id,
            )
            return None
        return artifact
