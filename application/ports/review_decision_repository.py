from __future__ import annotations

from typing import Protocol

from core.types import ReviewCaseId, ReviewDecisionId
from review.review_decision import ReviewDecision
from review.review_type import ReviewOutcome


class ReviewDecisionRepository(Protocol):

    def save(self, decision: ReviewDecision) -> None: ...

    def get(
        self,
        decision_id: ReviewDecisionId,
    ) -> ReviewDecision | None: ...

    def exists(
        self,
        decision_id: ReviewDecisionId,
    ) -> bool: ...

    def get_by_case(
        self,
        review_id: ReviewCaseId,
    ) -> ReviewDecision | None: ...

    def list_by_outcome(
        self,
        outcome: ReviewOutcome,
    ) -> tuple[ReviewDecision, ...]: ...
