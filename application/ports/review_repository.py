from __future__ import annotations

from typing import Protocol

from review.review_case_status import ReviewCaseStatus
from review.review_case_type import ReviewCaseType

from core.types import EntityId, FactId, ReviewCaseId, ReviewerId
from review.review_case import ReviewCase
from review.review_decision import ReviewDecision


class ReviewRepository(Protocol):

    def save_case(self, case: ReviewCase) -> None: ...

    def get_case(
        self,
        case_id: ReviewCaseId,
    ) -> ReviewCase | None: ...

    def get_decision_by_case(
        self,
        case_id: ReviewCaseId,
    ) -> ReviewDecision | None: ...

    def get_open_case_by_fact(
        self,
        fact_id: FactId,
    ) -> ReviewCase | None: ...

    def list_cases_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[ReviewCase, ...]: ...

    def list_cases_by_status(
        self,
        status: ReviewCaseStatus,
    ) -> tuple[ReviewCase, ...]: ...

    def list_cases_by_type(
        self,
        case_type: ReviewCaseType,
    ) -> tuple[ReviewCase, ...]: ...

    def list_cases_by_reviewer(
        self,
        reviewer_id: ReviewerId,
    ) -> tuple[ReviewCase, ...]: ...

    def close(
        self,
        case_id: ReviewCaseId,
        decision: ReviewDecision,
    ) -> None: ...
