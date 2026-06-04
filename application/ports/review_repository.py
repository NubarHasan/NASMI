from __future__ import annotations

from typing import Protocol

from core.types import EntityId, ReviewCaseId, UserId
from review.review_case import ReviewCase
from review.review_type import ReviewPriority, ReviewStatus


class ReviewRepository(Protocol):

    def save(self, case: ReviewCase) -> None: ...

    def get(
        self,
        case_id: ReviewCaseId,
    ) -> ReviewCase | None: ...

    def exists(
        self,
        case_id: ReviewCaseId,
    ) -> bool: ...

    def get_open_by_candidate_fact(
        self,
        candidate_fact_id: str,
    ) -> ReviewCase | None: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[ReviewCase, ...]: ...

    def list_by_status(
        self,
        status: ReviewStatus,
    ) -> tuple[ReviewCase, ...]: ...

    def list_by_assignee(
        self,
        user_id: UserId,
    ) -> tuple[ReviewCase, ...]: ...

    def list_by_priority(
        self,
        priority: ReviewPriority,
    ) -> tuple[ReviewCase, ...]: ...
