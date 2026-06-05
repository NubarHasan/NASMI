from __future__ import annotations

import logging

from core.guards import require
from pipeline.job import JobType
from pipeline.job_handler import JobHandler

_log = logging.getLogger(__name__)


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
