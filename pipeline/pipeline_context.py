from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import generate_job_id
from core.time import utcnow_iso
from pipeline.artifact import Artifact, ArtifactBundle, ArtifactType
from pipeline.failure import (
    FailureCollection,
    FailureSeverity,
    PipelineFailure,
)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVIEW = "review"


class RecoveryDecision(StrEnum):
    CONTINUE = "continue"
    RETRY = "retry"
    SKIP = "skip"
    REVIEW = "review"
    HALT = "halt"


_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PENDING: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.REVIEW}
    ),
    JobStatus.REVIEW: frozenset(
        {JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


@dataclass
class PipelineContext:
    job_id: str
    entity_id: str
    created_at: str

    _status: JobStatus = field(default=JobStatus.PENDING, repr=False, init=False)
    _artifacts: ArtifactBundle = field(repr=False, init=False)
    _failures: FailureCollection = field(repr=False, init=False)
    _metadata: dict[str, Any] = field(default_factory=dict, repr=False, init=False)
    _cancelled: bool = field(default=False, repr=False, init=False)
    _started_at: str | None = field(default=None, repr=False, init=False)
    _updated_at: str = field(default="", repr=False, init=False)

    def __post_init__(self) -> None:
        require(bool(self.job_id), "job_id must be non-empty")
        require(bool(self.entity_id), "entity_id must be non-empty")
        self._artifacts = ArtifactBundle(job_id=self.job_id)
        self._failures = FailureCollection(job_id=self.job_id)
        self._updated_at = self.created_at

    @property
    def status(self) -> JobStatus:
        return self._status

    @property
    def started_at(self) -> str | None:
        return self._started_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    def _touch(self) -> None:
        self._updated_at = utcnow_iso()

    def transition(self, new_status: JobStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self._status, frozenset())
        require(
            new_status in allowed,
            f"invalid transition: {self._status!r} → {new_status!r}",
        )
        if new_status == JobStatus.RUNNING and self._started_at is None:
            self._started_at = utcnow_iso()
        self._status = new_status
        self._touch()

    def cancel(self) -> None:
        if self._status not in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ):
            self._cancelled = True
            self.transition(JobStatus.CANCELLED)

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    def emit_artifact(self, artifact: Artifact) -> None:
        require(
            self._status == JobStatus.RUNNING,
            f"cannot emit artifact — status is {self._status!r}, expected RUNNING",
        )
        self._artifacts.add(artifact)
        self._touch()

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def artifacts_by_type(self, artifact_type: ArtifactType) -> list[Artifact]:
        return self._artifacts.by_type(artifact_type)

    def artifacts_by_stage(self, stage: str) -> list[Artifact]:
        return self._artifacts.by_stage(stage)

    def all_artifacts(self) -> list[Artifact]:
        return self._artifacts.all()

    def record_failure(self, failure: PipelineFailure) -> RecoveryDecision:
        require(
            self._status == JobStatus.RUNNING,
            f"cannot record failure — status is {self._status!r}, expected RUNNING",
        )
        self._failures.add(failure)
        decision = self._decide(failure)
        transitioned = self._apply_decision(decision)
        if not transitioned:
            self._touch()
        return decision

    def _decide(self, failure: PipelineFailure) -> RecoveryDecision:
        if failure.is_critical():
            return RecoveryDecision.HALT
        if failure.requires_review:
            return RecoveryDecision.REVIEW
        if failure.is_retryable:
            return RecoveryDecision.RETRY
        if failure.severity == FailureSeverity.WARNING:
            return RecoveryDecision.SKIP
        if failure.severity == FailureSeverity.INFO:
            return RecoveryDecision.CONTINUE
        return RecoveryDecision.SKIP

    def _apply_decision(self, decision: RecoveryDecision) -> bool:
        if decision == RecoveryDecision.HALT:
            self.transition(JobStatus.FAILED)
            return True
        if decision == RecoveryDecision.REVIEW:
            self.transition(JobStatus.REVIEW)
            return True
        return False

    def get_failure(self, failure_id: str) -> PipelineFailure | None:
        return self._failures.get(failure_id)

    def failures_by_stage(self, stage: str) -> list[PipelineFailure]:
        return self._failures.by_stage(stage)

    def all_failures(self) -> list[PipelineFailure]:
        return self._failures.all()

    def should_halt(self) -> bool:
        return self._failures.has_critical()

    def requires_review(self) -> bool:
        return self._failures.requires_review()

    def has_critical_failures(self) -> bool:
        return self._failures.has_critical()

    def has_retryable_failures(self) -> bool:
        return self._failures.has_retryable()

    def set_metadata(self, key: str, value: Any) -> None:
        require(bool(key), "metadata key must be non-empty")
        self._metadata[key] = copy.deepcopy(value)
        self._touch()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return copy.deepcopy(self._metadata.get(key, default))

    def all_metadata(self) -> dict[str, Any]:
        return copy.deepcopy(self._metadata)

    def metrics(self) -> dict[str, Any]:
        failure_summary = self._failures.summary()
        return {
            "job_id": self.job_id,
            "entity_id": self.entity_id,
            "status": str(self._status),
            "is_cancelled": self._cancelled,
            "artifact_count": len(self._artifacts),
            "artifact_summary": self._artifacts.summary(),
            "failure_count": failure_summary["total"],
            "failure_summary": failure_summary,
            "critical_failures": failure_summary["critical"],
            "review_required": failure_summary["review_required"],
            "created_at": self.created_at,
            "started_at": self._started_at,
            "updated_at": self._updated_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "started_at": self._started_at,
            "updated_at": self._updated_at,
            "status": str(self._status),
            "cancelled": self._cancelled,
            "artifacts": self._artifacts.to_dict(),
            "failures": self._failures.to_dict(),
            "metadata": copy.deepcopy(self._metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineContext:
        ctx = cls(
            job_id=data["job_id"],
            entity_id=data["entity_id"],
            created_at=data["created_at"],
        )
        ctx._status = JobStatus(data["status"])
        ctx._cancelled = data.get("cancelled", False)
        ctx._started_at = data.get("started_at")
        ctx._updated_at = data.get("updated_at", data["created_at"])
        ctx._artifacts = ArtifactBundle.from_dict(data["artifacts"])
        ctx._failures = FailureCollection.from_dict(data["failures"])
        ctx._metadata = copy.deepcopy(data.get("metadata", {}))
        return ctx

    @classmethod
    def create(cls, entity_id: str) -> PipelineContext:
        require(bool(entity_id), "entity_id must be non-empty")
        return cls(
            job_id=generate_job_id(),
            entity_id=entity_id,
            created_at=utcnow_iso(),
        )
