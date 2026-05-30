from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

from core.guards import require
from pipeline.dispatcher import Dispatcher
from pipeline.job import Job, JobPriority, JobStatus, JobType
from pipeline.job_queue import JobQueue
from pipeline.job_repository import JobRepository
from pipeline.worker import BaseWorker

_log = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        worker: BaseWorker,
        dispatcher: Dispatcher | None = None,
        *,
        max_retries: int = 3,
        retry_delay: int = 30,
        poll_interval: int | float = 1.0,
    ) -> None:
        require(isinstance(queue, JobQueue), "queue must be a JobQueue")
        require(
            isinstance(repository, JobRepository),
            "repository must implement JobRepository",
        )
        require(isinstance(worker, BaseWorker), "worker must be a BaseWorker")
        require(
            dispatcher is None or isinstance(dispatcher, Dispatcher),
            "dispatcher must be a Dispatcher",
        )

        self._queue = queue
        self._repository = repository
        self._worker = worker
        self._dispatcher = dispatcher or Dispatcher(
            queue=queue,
            repository=repository,
            worker=worker,
            max_retries=max_retries,
            retry_delay=retry_delay,
            poll_interval=poll_interval,
        )

    def start(self) -> None:
        self._dispatcher.start()
        _log.info("PipelineService started")

    def stop(self) -> None:
        self._dispatcher.stop()
        _log.info("PipelineService stop requested")

    def join(self, timeout: float | None = None) -> None:
        self._dispatcher.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._dispatcher.is_running

    def __enter__(self) -> PipelineService:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()
        self.join(timeout=5.0)

    def submit(
        self,
        job_type: JobType,
        payload: dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
    ) -> str:
        require(isinstance(job_type, JobType), "job_type must be a JobType")
        require(
            isinstance(payload, dict) and bool(payload),
            "payload must be a non-empty dict",
        )
        require(isinstance(priority, JobPriority), "priority must be a JobPriority")
        require(
            isinstance(max_retries, int) and max_retries >= 0,
            "max_retries must be non-negative int",
        )

        job = Job.create(
            job_type=job_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
        )
        self._repository.save(job)
        self._queue.enqueue(job.job_id, int(job.priority), job.created_at)
        _log.info(
            "job %r submitted (type=%s priority=%s)", job.job_id, job_type, priority
        )
        return job.job_id

    def get_job(self, job_id: str) -> Job | None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        return self._repository.load(job_id)

    def status(self, job_id: str) -> JobStatus | None:
        job = self.get_job(job_id)
        return job.status if job is not None else None

    def cancel(self, job_id: str) -> bool:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        job = self._repository.load(job_id)
        if job is None or job.is_terminal:
            return False
        job.cancel()
        self._queue.cancel(job_id)
        self._repository.save(job)
        _log.info("job %r cancelled", job_id)
        return True

    def list_by_status(self, status: JobStatus) -> list[Job]:
        require(isinstance(status, JobStatus), "status must be a JobStatus")
        return self._repository.list_by_status(status)

    def list_all(self) -> list[Job]:
        return self._repository.list_all()
