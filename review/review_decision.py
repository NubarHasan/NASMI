from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_review_decision_id,
    is_valid_review_case_id,
    is_valid_review_decision_id,
)
from core.time import is_valid_timestamp
from core.types import ReviewCaseId, ReviewDecisionId
from review.review_type import ReviewOutcome


@dataclass(frozen=True)
class ReviewDecision:
    decision_id: ReviewDecisionId
    review_id: ReviewCaseId
    decided_by: str
    decided_at: str
    outcome: ReviewOutcome
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_review_decision_id(self.decision_id),
            f"Invalid ReviewDecisionId: [{self.decision_id}]",
        )
        require(
            is_valid_review_case_id(self.review_id),
            f"Invalid ReviewCaseId: [{self.review_id}]",
        )
        require(
            bool(self.decided_by.strip()),
            "decided_by must not be empty",
        )
        require(
            is_valid_timestamp(self.decided_at),
            f"Invalid decided_at timestamp: [{self.decided_at}]",
        )
        require(
            bool(self.rationale.strip()),
            "rationale must not be empty",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    def with_metadata(self, key: str, value: Any) -> ReviewDecision:
        return ReviewDecision(
            decision_id=self.decision_id,
            review_id=self.review_id,
            decided_by=self.decided_by,
            decided_at=self.decided_at,
            outcome=self.outcome,
            rationale=self.rationale,
            metadata={**self.metadata, key: value},
        )

    @property
    def is_approved(self) -> bool:
        return self.outcome == ReviewOutcome.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.outcome == ReviewOutcome.REJECTED

    @property
    def is_escalated(self) -> bool:
        return self.outcome == ReviewOutcome.ESCALATED

    @classmethod
    def create(
        cls,
        review_id: ReviewCaseId,
        decided_by: str,
        decided_at: str,
        outcome: ReviewOutcome,
        rationale: str,
        metadata: dict[str, Any] | None = None,
    ) -> ReviewDecision:
        return cls(
            decision_id=generate_review_decision_id(),
            review_id=review_id,
            decided_by=decided_by,
            decided_at=decided_at,
            outcome=outcome,
            rationale=rationale,
            metadata=dict(metadata) if metadata is not None else {},
        )
