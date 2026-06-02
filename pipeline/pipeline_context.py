from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from core.guards import require
from core.time import format_timestamp, parse_timestamp, utcnow
from pipeline.artifact import Artifact, ArtifactBundle
from pipeline.failure import FailureCollection, PipelineFailure


class RecoveryDecision(StrEnum):
    CONTINUE = "continue"
    RETRY = "retry"
    ABORT = "abort"
    ESCALATE = "escalate"


@dataclass
class PipelineContext:
    job_id: str
    created_at: datetime
    current_stage: str
    artifacts: ArtifactBundle
    failures: FailureCollection
    metadata: dict[str, Any]

    _stage_history: list[str] = field(default_factory=list, repr=False, init=False)

    @classmethod
    def create(cls, job_id: str) -> PipelineContext:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        return cls(
            job_id=job_id,
            created_at=utcnow(),
            current_stage="",
            artifacts=ArtifactBundle(job_id=job_id),
            failures=FailureCollection(job_id=job_id),
            metadata={},
        )

    def set_stage(self, stage: str) -> None:
        require(isinstance(stage, str) and bool(stage), "stage must be non-empty")
        if stage == self.current_stage:
            return
        if self.current_stage:
            self._stage_history.append(self.current_stage)
        self.current_stage = stage

    @property
    def stage_history(self) -> list[str]:
        return list(self._stage_history)

    def add_artifact(self, artifact: Artifact) -> None:
        require(artifact is not None, "artifact must not be None")
        self.artifacts.add(artifact)

    def add_failure(self, failure: PipelineFailure) -> None:
        require(failure is not None, "failure must not be None")
        self.failures.add(failure)

    def recovery_decision(self) -> RecoveryDecision:
        all_failures = self.failures.all()

        if not all_failures:
            return RecoveryDecision.CONTINUE

        if any(f.is_critical() for f in all_failures):
            return RecoveryDecision.ABORT

        if any(f.is_retryable for f in all_failures):
            return RecoveryDecision.RETRY

        if any(f.requires_review for f in all_failures):
            return RecoveryDecision.ESCALATE

        return RecoveryDecision.ABORT

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "created_at": format_timestamp(self.created_at),
            "current_stage": self.current_stage,
            "stage_history": list(self._stage_history),
            "artifacts": self.artifacts.to_dict(),
            "failures": self.failures.to_dict(),
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineContext:
        ctx = cls(
            job_id=data["job_id"],
            created_at=parse_timestamp(data["created_at"]),
            current_stage=data.get("current_stage", ""),
            artifacts=ArtifactBundle.from_dict(
                data.get("artifacts", {"job_id": data["job_id"], "items": []})
            ),
            failures=FailureCollection.from_dict(
                data.get("failures", {"job_id": data["job_id"], "items": []})
            ),
            metadata=copy.deepcopy(data.get("metadata", {})),
        )
        ctx._stage_history = list(data.get("stage_history", []))
        return ctx
