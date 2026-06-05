from __future__ import annotations

import logging

from core.guards import require
from core.types import EntityId
from pipeline.artifact import FactAcceptanceArtifact
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job, JobType
from processing.fact_acceptance.fact_acceptance_service import FactAcceptanceService

_log = logging.getLogger(__name__)

_STAGE = "fact_acceptance"


class FactAcceptanceHandler:

    def __init__(self, service: FactAcceptanceService) -> None:
        require(
            isinstance(service, FactAcceptanceService),
            "service must be a FactAcceptanceService",
        )
        self._service = service

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        require(
            job.job_type == JobType.FACT_ACCEPTANCE,
            f"expected FACT_ACCEPTANCE job, got {job.job_type!r}",
        )

        job.advance_stage(_STAGE)

        payload = job.get_payload()
        entity_id_raw = payload.get("entity_id")

        if not entity_id_raw:
            job.context.failures.add(
                _failure(job.job_id, "entity_id missing from job payload")
            )
            return

        entity_id = EntityId(str(entity_id_raw))

        _log.info("FactAcceptanceHandler — entity=%s", entity_id)

        try:
            result = self._service.process(entity_id)
        except Exception as exc:
            _log.exception("FactAcceptanceHandler failed — %s", exc)
            job.context.failures.add(_failure(job.job_id, str(exc)))
            return

        _log.info(
            "fact_acceptance done — accepted=%d review=%d conflicts=%d rejected=%d",
            len(result.accepted_facts),
            len(result.review_cases),
            len(result.conflicts),
            len(result.rejected_facts),
        )

        snapshot = {
            "entity_id": str(entity_id),
            "accepted_count": len(result.accepted_facts),
            "review_required_count": len(result.review_cases),
            "conflict_count": len(result.conflicts),
            "rejected_count": len(result.rejected_facts),
            "accepted_fact_ids": [str(f.fact_id) for f in result.accepted_facts],
            "review_case_ids": [str(c.review_case_id) for c in result.review_cases],
            "conflict_ids": [str(c.conflict_id) for c in result.conflicts],
            "rejected_fact_ids": [str(f.fact_id) for f in result.rejected_facts],
        }

        artifact = FactAcceptanceArtifact.create(
            job_id=job.job_id,
            stage=_STAGE,
            entity_id=str(entity_id),
            accepted_count=len(result.accepted_facts),
            review_required_count=len(result.review_cases),
            conflict_count=len(result.conflicts),
            rejected_count=len(result.rejected_facts),
            snapshot=snapshot,
        )

        job.context.artifacts.add(artifact)


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
