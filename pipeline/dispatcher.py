from __future__ import annotations

import logging
import threading

from core.guards import require
from pipeline.failure import (
    FailureCategory,
    FailureSeverity,
    FailureSource,
    PipelineFailure,
)
from pipeline.job import Job
from pipeline.job_queue import JobQueue
from pipeline.job_repository import JobRepository
from pipeline.pipeline_context import RecoveryDecision
from pipeline.worker import BaseWorker

_log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        worker: BaseWorker,
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
        require(isinstance(max_retries, int), "max_retries must be an int")
        require(isinstance(retry_delay, int), "retry_delay must be an int")
        require(
            isinstance(poll_interval, (int, float)), "poll_interval must be numeric"
        )
        require(max_retries >= 0, "max_retries must be non-negative")
        require(retry_delay >= 0, "retry_delay must be non-negative")
        require(poll_interval > 0, "poll_interval must be positive")

        self._queue = queue
        self._repository = repository
        self._worker = worker
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._poll_interval = float(poll_interval)
        self._running = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        require(not self.is_running, "dispatcher already running")
        self._running.set()
        self._thread = threading.Thread(
            target=self._loop, name="dispatcher", daemon=True
        )
        self._thread.start()
        _log.info("Dispatcher started")

    def stop(self) -> None:
        self._running.clear()
        _log.info("Dispatcher stop requested")

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def _loop(self) -> None:
        while self._running.is_set():
            try:
                self._tick()
            except Exception:
                _log.exception("unexpected error in dispatcher loop")
            self._running.wait(timeout=self._poll_interval)

    def _tick(self) -> None:
        job_id = self._queue.lease()
        if job_id is None:
            return

        job = self._repository.load(job_id)
        if job is None:
            _log.error("leased job not found in repository: %s", job_id)
            self._queue.fail(job_id)
            return

        job.start()
        self._repository.save(job)

        try:
            self._worker.execute(job)
        except Exception as exc:
            _log.exception("unhandled exception from worker: %s", job_id)
            failure = PipelineFailure.create(
                job_id=job.job_id,
                stage=job.current_stage,
                category=FailureCategory.SYSTEM,
                severity=FailureSeverity.CRITICAL,
                source=FailureSource.SYSTEM,
                message=str(exc),
                is_retryable=False,
                requires_review=False,
            )
            job.context.add_failure(failure)

        self._route(job)

    def _route(self, job: Job) -> None:
        decision = job.context.recovery_decision()

        if decision == RecoveryDecision.CONTINUE:
            job.complete()
            self._repository.save(job)
            self._queue.complete(job.job_id)
            _log.info("job completed: %s", job.job_id)

        elif decision == RecoveryDecision.RETRY:
            if job.can_retry:
                job.mark_retrying()
                self._repository.save(job)
                self._queue.requeue(job.job_id, self._retry_delay)
                _log.info("job requeued: %s (attempt %d)", job.job_id, job.retry_count)
            else:
                job.fail()
                self._repository.save(job)
                self._queue.fail(job.job_id)
                _log.error("job exhausted retries: %s", job.job_id)

        elif decision == RecoveryDecision.ESCALATE:
            job.fail()
            self._repository.save(job)
            self._queue.fail(job.job_id)
            _log.warning("job escalated to review: %s", job.job_id)

        else:
            job.fail()
            self._repository.save(job)
            self._queue.fail(job.job_id)
            _log.error("job aborted: %s", job.job_id)
