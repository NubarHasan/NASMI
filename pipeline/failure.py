from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import generate_failure_id
from core.time import utcnow_iso


class FailureSeverity(StrEnum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FailureCategory(StrEnum):
    IO = "io"
    VALIDATION = "validation"
    PARSING = "parsing"
    OCR = "ocr"
    EXTRACTION = "extraction"
    KNOWLEDGE = "knowledge"
    CONFLICT = "conflict"
    REVIEW = "review"
    SYSTEM = "system"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class FailureSource(StrEnum):
    SYSTEM = "system"
    USER = "user"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PipelineFailure:
    failure_id: str
    job_id: str
    stage: str
    category: FailureCategory
    severity: FailureSeverity
    source: FailureSource
    message: str
    metadata: dict[str, Any]
    is_retryable: bool
    requires_review: bool
    artifact_ids: tuple[str, ...]
    created_at: str

    def is_critical(self) -> bool:
        return self.severity == FailureSeverity.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "job_id": self.job_id,
            "stage": self.stage,
            "category": str(self.category),
            "severity": str(self.severity),
            "source": str(self.source),
            "message": self.message,
            "metadata": copy.deepcopy(self.metadata),
            "is_retryable": self.is_retryable,
            "requires_review": self.requires_review,
            "artifact_ids": list(self.artifact_ids),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineFailure:
        return cls(
            failure_id=data["failure_id"],
            job_id=data["job_id"],
            stage=data["stage"],
            category=FailureCategory(data["category"]),
            severity=FailureSeverity(data["severity"]),
            source=FailureSource(data["source"]),
            message=data["message"],
            metadata=copy.deepcopy(data.get("metadata", {})),
            is_retryable=data["is_retryable"],
            requires_review=data["requires_review"],
            artifact_ids=tuple(data.get("artifact_ids", [])),
            created_at=data["created_at"],
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        category: FailureCategory,
        severity: FailureSeverity,
        source: FailureSource,
        message: str,
        is_retryable: bool,
        requires_review: bool,
        metadata: dict[str, Any] | None = None,
        artifact_ids: tuple[str, ...] = (),
    ) -> PipelineFailure:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(message), "message must be non-empty")
        require(
            all(isinstance(x, str) and x for x in artifact_ids),
            "artifact_ids must contain non-empty strings",
        )
        return cls(
            failure_id=generate_failure_id(),
            job_id=job_id,
            stage=stage,
            category=category,
            severity=severity,
            source=source,
            message=message,
            metadata=copy.deepcopy(metadata) if metadata else {},
            is_retryable=is_retryable,
            requires_review=requires_review,
            artifact_ids=artifact_ids,
            created_at=utcnow_iso(),
        )


@dataclass(frozen=True)
class FailureSnapshot:
    failure_id: str
    stage: str
    category: str
    severity: str
    message: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "stage": self.stage,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "created_at": self.created_at,
        }

    @classmethod
    def from_failure(cls, failure: PipelineFailure) -> FailureSnapshot:
        return cls(
            failure_id=failure.failure_id,
            stage=failure.stage,
            category=str(failure.category),
            severity=str(failure.severity),
            message=failure.message,
            created_at=failure.created_at,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureSnapshot:
        return cls(
            failure_id=data["failure_id"],
            stage=data["stage"],
            category=data["category"],
            severity=data["severity"],
            message=data["message"],
            created_at=data["created_at"],
        )


@dataclass
class FailureCollection:
    job_id: str

    _order: list[PipelineFailure] = field(default_factory=list, repr=False, init=False)
    _by_id: dict[str, PipelineFailure] = field(
        default_factory=dict, repr=False, init=False
    )
    _by_category: dict[FailureCategory, list[PipelineFailure]] = field(
        default_factory=dict, repr=False, init=False
    )
    _by_severity: dict[FailureSeverity, list[PipelineFailure]] = field(
        default_factory=dict, repr=False, init=False
    )
    _by_stage: dict[str, list[PipelineFailure]] = field(
        default_factory=dict, repr=False, init=False
    )

    def add(self, failure: PipelineFailure) -> None:
        require(
            failure.job_id == self.job_id,
            f"failure.job_id {failure.job_id!r} != collection.job_id {self.job_id!r}",
        )
        require(
            failure.failure_id not in self._by_id,
            f"duplicate failure_id: {failure.failure_id!r}",
        )
        self._order.append(failure)
        self._by_id[failure.failure_id] = failure
        self._by_category.setdefault(failure.category, []).append(failure)
        self._by_severity.setdefault(failure.severity, []).append(failure)
        self._by_stage.setdefault(failure.stage, []).append(failure)

    def get(self, failure_id: str) -> PipelineFailure | None:
        return self._by_id.get(failure_id)

    def by_category(self, category: FailureCategory) -> list[PipelineFailure]:
        return list(self._by_category.get(category, []))

    def by_severity(self, severity: FailureSeverity) -> list[PipelineFailure]:
        return list(self._by_severity.get(severity, []))

    def by_stage(self, stage: str) -> list[PipelineFailure]:
        return list(self._by_stage.get(stage, []))

    def all(self) -> list[PipelineFailure]:
        return list(self._order)

    def ordered(self) -> list[tuple[int, PipelineFailure]]:
        return list(enumerate(self._order))

    def sequence_of(self, failure_id: str) -> int | None:
        for idx, failure in enumerate(self._order):
            if failure.failure_id == failure_id:
                return idx
        return None

    def has_critical(self) -> bool:
        return bool(self._by_severity.get(FailureSeverity.CRITICAL))

    def requires_review(self) -> bool:
        return any(f.requires_review for f in self._order)

    def has_retryable(self) -> bool:
        return any(f.is_retryable for f in self._order)

    def critical_count(self) -> int:
        return len(self._by_severity.get(FailureSeverity.CRITICAL, []))

    def error_count(self) -> int:
        return len(self._by_severity.get(FailureSeverity.ERROR, []))

    def warning_count(self) -> int:
        return len(self._by_severity.get(FailureSeverity.WARNING, []))

    def info_count(self) -> int:
        return len(self._by_severity.get(FailureSeverity.INFO, []))

    def summary(self) -> dict[str, int]:
        return {
            "critical": self.critical_count(),
            "error": self.error_count(),
            "warning": self.warning_count(),
            "info": self.info_count(),
            "review_required": sum(1 for f in self._order if f.requires_review),
            "retryable": sum(1 for f in self._order if f.is_retryable),
            "total": len(self._order),
        }

    def snapshots(self) -> list[FailureSnapshot]:
        return [FailureSnapshot.from_failure(f) for f in self._order]

    def __len__(self) -> int:
        return len(self._order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "items": [f.to_dict() for f in self._order],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureCollection:
        collection = cls(job_id=data["job_id"])
        for item in data.get("items", []):
            collection.add(PipelineFailure.from_dict(item))
        return collection
