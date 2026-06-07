from __future__ import annotations

import logging

from core.guards import require
from pipeline.job import Job
from pipeline.job_handler import JobHandler

_log = logging.getLogger(__name__)

_ORDERED_STAGES = (
    "document_import",
    "ocr",
    "classification",
    "extraction",
    "entity_resolution",
    "knowledge_build",
    "fact_acceptance",
    "profile_build",
    "output_build",
)


class SequentialPipelineHandler:

    def __init__(self, handlers: dict[str, JobHandler]) -> None:
        require(isinstance(handlers, dict), "handlers must be a dict")
        for stage in _ORDERED_STAGES:
            require(
                stage in handlers,
                f"missing handler for stage: {stage!r}",
            )
        self._handlers: dict[str, JobHandler] = dict(handlers)

    def handle(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        _log.info("pipeline started — job_id=%r", job.job_id)

        for stage in _ORDERED_STAGES:
            if job.context.failures.has_critical():
                _log.warning(
                    "pipeline aborted at stage %r due to critical failure — job_id=%r",
                    stage,
                    job.job_id,
                )
                return

            job.context.set_stage(stage)
            _log.debug("executing stage %r — job_id=%r", stage, job.job_id)
            self._handlers[stage].handle(job)

        _log.info("pipeline completed — job_id=%r", job.job_id)
