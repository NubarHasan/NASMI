from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_review_case_id,
    is_valid_candidate_fact_id,
    is_valid_entity_id,
    is_valid_evidence_id,
    is_valid_review_case_id,
    is_valid_user_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import (
    CandidateFactId,
    ConfidenceScore,
    EntityId,
    EvidenceId,
    ReviewCaseId,
    UserId,
)
from review.review_type import ReviewPriority, ReviewStatus


@dataclass(frozen=True)
class ReviewCase:
    review_case_id: ReviewCaseId
    entity_id: EntityId
    candidate_fact_id: CandidateFactId
    fact_type: str
    raw_value: str
    normalized_value: str
    confidence: ConfidenceScore
    evidence_ids: tuple[EvidenceId, ...]
    status: ReviewStatus
    priority: ReviewPriority
    created_at: str  # ISO-8601, توافقاً مع بقية النظام
    assigned_to: UserId | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_review_case_id(self.review_case_id),
            f"Invalid ReviewCaseId: [{self.review_case_id}]",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"Invalid EntityId: [{self.entity_id}]",
        )
        require(
            is_valid_candidate_fact_id(self.candidate_fact_id),
            f"Invalid CandidateFactId: [{self.candidate_fact_id}]",
        )
        require(
            bool(self.fact_type.strip()),
            "fact_type must not be empty",
        )
        require(
            bool(self.raw_value.strip()),
            "raw_value must not be empty",
        )
        require(
            bool(self.normalized_value.strip()),
            "normalized_value must not be empty",
        )
        require(
            0.0 <= self.confidence <= 1.0,
            f"confidence must be between 0.0 and 1.0, got [{self.confidence}]",
        )
        require(
            isinstance(self.evidence_ids, tuple),
            "evidence_ids must be a tuple",
        )
        require(
            len(self.evidence_ids) > 0,
            "evidence_ids must not be empty",
        )
        require(
            all(is_valid_evidence_id(e) for e in self.evidence_ids),
            "one or more evidence_ids are invalid",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"Invalid created_at timestamp: [{self.created_at}]",
        )
        require(
            self.assigned_to is None or is_valid_user_id(self.assigned_to),
            f"Invalid UserId: [{self.assigned_to}]",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    def assign(self, reviewer: UserId) -> ReviewCase:
        require(is_valid_user_id(reviewer), f"Invalid UserId: [{reviewer}]")
        return replace(self, assigned_to=reviewer, status=ReviewStatus.ASSIGNED)

    def start_review(self) -> ReviewCase:
        require(
            self.status == ReviewStatus.ASSIGNED,
            f"Cannot start review from status [{self.status}]",
        )
        return replace(self, status=ReviewStatus.IN_REVIEW)

    def complete(self) -> ReviewCase:
        require(
            self.status == ReviewStatus.IN_REVIEW,
            f"Cannot complete from status [{self.status}]",
        )
        return replace(self, status=ReviewStatus.COMPLETED)

    def cancel(self) -> ReviewCase:
        require(
            self.status not in (ReviewStatus.COMPLETED, ReviewStatus.CANCELLED),
            f"Cannot cancel from status [{self.status}]",
        )
        return replace(self, status=ReviewStatus.CANCELLED)

    def escalate(self) -> ReviewCase:
        """
        يُعيد الحالة إلى PENDING مع رفع الأولوية إلى CRITICAL.
        يُسجَّل الـ Outcome=ESCALATED لاحقاً عبر ReviewDecision —
        لا توجد حالة ESCALATED مستقلة في ReviewStatus.
        """
        require(
            self.status == ReviewStatus.IN_REVIEW,
            f"Cannot escalate from status [{self.status}]",
        )
        return replace(
            self, priority=ReviewPriority.CRITICAL, status=ReviewStatus.PENDING
        )

    def with_metadata(self, key: str, value: Any) -> ReviewCase:
        return replace(self, metadata={**self.metadata, key: value})

    @property
    def is_open(self) -> bool:
        return self.status not in (ReviewStatus.COMPLETED, ReviewStatus.CANCELLED)

    @property
    def is_assigned(self) -> bool:
        return self.assigned_to is not None

    @classmethod
    def create(
        cls,
        entity_id: EntityId,
        candidate_fact_id: CandidateFactId,
        fact_type: str,
        raw_value: str,
        normalized_value: str,
        confidence: ConfidenceScore,
        evidence_ids: tuple[EvidenceId, ...],
        priority: ReviewPriority = ReviewPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> ReviewCase:
        return cls(
            review_case_id=generate_review_case_id(),
            entity_id=entity_id,
            candidate_fact_id=candidate_fact_id,
            fact_type=fact_type,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=confidence,
            evidence_ids=evidence_ids,
            status=ReviewStatus.PENDING,
            priority=priority,
            created_at=utcnow_iso(),
            assigned_to=None,
            metadata=dict(metadata) if metadata is not None else {},
        )
