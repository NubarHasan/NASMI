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
from pipeline.worker import Worker

_log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        worker: Worker,
        max_retries: int = 3,
        retry_delay: int = 30,
        poll_interval: int | float = 1.0,
    ) -> None:
        require(isinstance(queue, JobQueue), "queue must be a JobQueue")
        require(
            isinstance(repository, JobRepository),
            "repository must implement JobRepository",
        )
        require(isinstance(worker, Worker), "worker must implement Worker")
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

    def start(self) -> None:
        require(
            self._thread is None or not self._thread.is_alive(),
            "dispatcher already running",
        )
        self._running.set()
        self._thread = threading.Thread(
            target=self._loop, name="dispatcher", daemon=True
        )
        self._thread.start()
        _log.info("dispatcher started")

    def stop(self) -> None:
        self._running.clear()
        _log.info("dispatcher stop requested")

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while self._running.is_set():
            try:
                job_id = self._queue.lease()
                if job_id:
                    self._dispatch(job_id)
                else:
                    self._running.wait(timeout=self._poll_interval)
            except Exception:
                _log.exception("unhandled error in dispatcher loop — continuing")

    def _dispatch(self, job_id: str) -> None:
        job: Job | None = None
        try:
            job = self._repository.load(job_id)
            if job is None:
                _log.error("job %r not found in repository — skipping", job_id)
                self._queue.fail(job_id)
                return

            job.start()
            self._repository.save(job)
            self._worker.execute(job)

            decision = job.context.recovery_decision()
            self._apply_decision(job, job_id, decision)

        except Exception as exc:
            _log.exception("dispatch failed for job %r", job_id)
            if job is not None:
                self._record_dispatch_failure(job, exc)
                job.mark_failed()
                self._repository.save(job)
            try:
                self._queue.fail(job_id)
            except Exception:
                _log.exception("failed to mark job %r as failed in queue", job_id)

    def _apply_decision(
        self, job: Job, job_id: str, decision: RecoveryDecision
    ) -> None:
        if decision == RecoveryDecision.CONTINUE:
            job.complete()
            self._queue.complete(job_id)
            self._repository.save(job)
            _log.info("job %r completed", job_id)
            return

        if decision == RecoveryDecision.RETRY and job.retry_count < self._max_retries:
            job.mark_retrying()
            self._queue.requeue(job_id, delay_seconds=self._retry_delay)
            self._repository.save(job)
            _log.info(
                "job %r requeued (attempt %d/%d)",
                job_id,
                job.retry_count,
                self._max_retries,
            )
            return

        job.mark_failed()
        self._queue.fail(job_id)
        self._repository.save(job)
        _log.warning("job %r failed (decision=%s)", job_id, decision.value)

    def _record_dispatch_failure(self, job: Job, exc: Exception) -> None:
        failure = PipelineFailure.create(
            job_id=job.job_id,
            stage=job.context.current_stage or "dispatch",
            category=FailureCategory.SYSTEM,
            severity=FailureSeverity.CRITICAL,
            source=FailureSource.SYSTEM,
            message=str(exc),
            is_retryable=False,
            requires_review=True,
            metadata={"exception_type": type(exc).__name__},
        )
        job.context.failures.add(failure)
