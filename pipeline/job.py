from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any

from core.exceptions import StateError
from core.guards import require
from core.hashing import hash_json
from core.identifiers import generate_job_id
from core.time import format_timestamp, parse_timestamp, utcnow
from pipeline.pipeline_context import PipelineContext


class JobPriority(IntEnum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40


class JobType(StrEnum):
    DOCUMENT_IMPORT = "document_import"
    OCR = "ocr"
    EXTRACTION = "extraction"
    ENTITY_RESOLUTION = "entity_resolution"
    KNOWLEDGE_BUILD = "knowledge_build"
    FACT_ACCEPTANCE = "fact_acceptance"
    PROFILE_BUILD = "profile_build"
    FORM_FILL = "form_fill"
    EXPORT = "export"
    OUTPUT_BUILD = "output_build"
    DOCUMENT_PIPELINE = "document_pipeline"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PENDING: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RETRYING,
        }
    ),
    JobStatus.FAILED: frozenset({JobStatus.RETRYING, JobStatus.CANCELLED}),
    JobStatus.RETRYING: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


@dataclass
class Job:
    job_id: str
    job_type: JobType
    priority: JobPriority
    status: JobStatus
    created_at: datetime
    payload_hash: str
    context: PipelineContext

    _payload: dict[str, Any] = field(default_factory=dict, repr=False, init=False)
    _started_at: datetime | None = field(default=None, repr=False, init=False)
    _completed_at: datetime | None = field(default=None, repr=False, init=False)
    _cancelled_at: datetime | None = field(default=None, repr=False, init=False)
    _retry_count: int = field(default=0, repr=False, init=False)
    _max_retries: int = field(default=3, repr=False, init=False)
    _profile: Any = field(default=None, repr=False, init=False)

    @property
    def profile(self) -> Any:
        return self._profile

    def set_profile(self, profile: Any) -> None:
        require(profile is not None, "profile must not be None")
        self._profile = profile

    @property
    def bundle(self) -> Any:
        return self.context.artifacts

    def set_stage(self, stage: str) -> None:
        self.context.set_stage(stage)

    def advance_stage(self, stage: str) -> None:
        self.context.set_stage(stage)

    @property
    def current_stage(self) -> str:
        return self.context.current_stage

    @property
    def stage_history(self) -> list[str]:
        return self.context.stage_history

    def get_payload(self) -> dict[str, Any]:
        return copy.deepcopy(self._payload)

    def payload_copy(self) -> dict[str, Any]:
        return copy.deepcopy(self._payload)

    def _transition(self, target: JobStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise StateError(
                f"invalid job transition: {self.status} -> {target} "
                f"(job_id={self.job_id!r})"
            )
        self.status = target

    def start(self) -> None:
        self._transition(JobStatus.RUNNING)
        if self._started_at is None:
            self._started_at = utcnow()

    def complete(self) -> None:
        self._transition(JobStatus.COMPLETED)
        self._completed_at = utcnow()

    def fail(self) -> None:
        self._transition(JobStatus.FAILED)
        self._completed_at = utcnow()

    def cancel(self) -> None:
        self._transition(JobStatus.CANCELLED)
        self._cancelled_at = utcnow()

    def mark_retrying(self) -> None:
        require(self.can_retry, f"max retries reached ({self._max_retries})")
        self._transition(JobStatus.RETRYING)
        self._retry_count += 1
        self._completed_at = None

    def resume(self) -> None:
        self._transition(JobStatus.RUNNING)

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def cancelled_at(self) -> datetime | None:
        return self._cancelled_at

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def can_retry(self) -> bool:
        return self._retry_count < self._max_retries

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

    @property
    def is_active(self) -> bool:
        return self.status in {
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.RETRYING,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": str(self.job_type),
            "priority": int(self.priority),
            "status": str(self.status),
            "created_at": format_timestamp(self.created_at),
            "payload_hash": self.payload_hash,
            "payload": self.payload_copy(),
            "started_at": (
                format_timestamp(self._started_at) if self._started_at else None
            ),
            "completed_at": (
                format_timestamp(self._completed_at) if self._completed_at else None
            ),
            "cancelled_at": (
                format_timestamp(self._cancelled_at) if self._cancelled_at else None
            ),
            "retry_count": self._retry_count,
            "max_retries": self._max_retries,
            "context": self.context.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        context = PipelineContext.from_dict(data["context"])
        require(
            context.job_id == data["job_id"],
            f"job/context id mismatch: {data['job_id']!r} != {context.job_id!r}",
        )
        payload = data.get("payload", {})
        payload_hash = data["payload_hash"]
        require(hash_json(payload) == payload_hash, "payload hash mismatch")
        job = cls(
            job_id=data["job_id"],
            job_type=JobType(data["job_type"]),
            priority=JobPriority(data["priority"]),
            status=JobStatus(data["status"]),
            created_at=parse_timestamp(data["created_at"]),
            payload_hash=payload_hash,
            context=context,
        )
        job._payload = copy.deepcopy(payload)
        job._started_at = (
            parse_timestamp(data["started_at"]) if data.get("started_at") else None
        )
        job._completed_at = (
            parse_timestamp(data["completed_at"]) if data.get("completed_at") else None
        )
        job._cancelled_at = (
            parse_timestamp(data["cancelled_at"]) if data.get("cancelled_at") else None
        )
        job._retry_count = data.get("retry_count", 0)
        job._max_retries = data.get("max_retries", 3)
        return job

    @classmethod
    def create(
        cls,
        job_type: JobType,
        payload: dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
    ) -> Job:
        require(isinstance(job_type, JobType), "job_type must be a JobType")
        require(isinstance(payload, dict), "payload must be a dict")
        require(isinstance(priority, JobPriority), "priority must be a JobPriority")
        require(
            isinstance(max_retries, int) and max_retries >= 0,
            "max_retries must be a non-negative int",
        )
        job_id = generate_job_id()
        context = PipelineContext.create(job_id)
        job = cls(
            job_id=job_id,
            job_type=job_type,
            priority=priority,
            status=JobStatus.PENDING,
            created_at=utcnow(),
            payload_hash=hash_json(payload),
            context=context,
        )
        job._payload = copy.deepcopy(payload)
        job._max_retries = max_retries
        return job
