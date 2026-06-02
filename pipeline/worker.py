from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from core.guards import require
from core.types import Metadata
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job, JobType

_log = logging.getLogger(__name__)


@runtime_checkable
class JobHandler(Protocol):
    def handle(self, job: Job) -> None: ...


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[JobType, JobHandler] = {}

    def register(self, job_type: JobType, handler: JobHandler) -> None:
        require(isinstance(job_type, JobType), "job_type must be a JobType")
        require(isinstance(handler, JobHandler), "handler must implement JobHandler")
        require(
            job_type not in self._handlers,
            f"handler already registered for {job_type!r}",
        )
        self._handlers[job_type] = handler
        _log.debug("registered handler for %r: %s", job_type, type(handler).__name__)

    def resolve(self, job_type: JobType) -> JobHandler:
        handler = self._handlers.get(job_type)
        require(handler is not None, f"no handler registered for {job_type!r}")
        assert handler is not None
        return handler

    def registered_types(self) -> frozenset[JobType]:
        return frozenset(self._handlers)


class BaseWorker(ABC):
    @abstractmethod
    def execute(self, job: Job) -> None: ...


class DefaultWorker(BaseWorker):
    def __init__(self, registry: HandlerRegistry) -> None:
        require(
            isinstance(registry, HandlerRegistry), "registry must be a HandlerRegistry"
        )
        self._registry = registry

    def execute(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        handler = self._resolve_handler(job)
        if handler is None:
            return
        self._run_handler(job, handler)

    def _resolve_handler(self, job: Job) -> JobHandler | None:
        try:
            return self._registry.resolve(job.job_type)
        except Exception as exc:
            _log.error(
                "no handler for job %r (type=%r): %s",
                job.job_id,
                job.job_type,
                exc,
            )
            self._record_failure(
                job,
                stage="routing",
                category=FailureCategory.SYSTEM,
                source=FailureSource.SYSTEM,
                message=str(exc),
                severity=FailureSeverity.CRITICAL,
                is_retryable=False,
                metadata={"error_code": "NO_HANDLER"},
            )
            return None

    def _run_handler(self, job: Job, handler: JobHandler) -> None:
        try:
            _log.info(
                "executing job %r (type=%r, stage=%r)",
                job.job_id,
                job.job_type,
                job.current_stage,
            )
            handler.handle(job)
            _log.info("handler finished for job %r", job.job_id)
        except Exception as exc:
            _log.exception("handler raised for job %r", job.job_id)
            self._record_failure(
                job,
                stage=job.context.current_stage or "execution",
                category=FailureCategory.SYSTEM,
                source=FailureSource.SYSTEM,
                message=str(exc),
                severity=FailureSeverity.ERROR,
                is_retryable=True,
                metadata={
                    "error_code": "HANDLER_ERROR",
                    "exception_type": type(exc).__name__,
                },
            )

    @staticmethod
    def _record_failure(
        job: Job,
        stage: str,
        category: FailureCategory,
        source: FailureSource,
        message: str,
        severity: FailureSeverity,
        is_retryable: bool,
        metadata: Metadata | None = None,
    ) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=stage,
            category=category,
            source=source,
            message=message,
            severity=severity,
            is_retryable=is_retryable,
            requires_review=True,
            metadata=metadata or {},
        )
        job.context.failures.add(failure)
