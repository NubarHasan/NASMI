from __future__ import annotations

from collections.abc import Callable

from application.ports.review_unit_of_work import ReviewUnitOfWork
from core.guards import require
from core.identifiers import (
    is_valid_entity_id,
    is_valid_review_case_id,
    is_valid_user_id,
)
from core.time import utcnow_iso
from core.types import EntityId, ReviewCaseId, UserId
from review.review_case import ReviewCase
from review.review_decision import ReviewDecision
from review.review_type import ReviewOutcome, ReviewPriority, ReviewStatus


class ReviewApplicationService:

    def __init__(self, uow_factory: Callable[[], ReviewUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def open_case(self, case: ReviewCase) -> ReviewCase:
        require(isinstance(case, ReviewCase), "case must be a ReviewCase")
        require(case.status is ReviewStatus.PENDING, "new case must be PENDING")

        with self._uow_factory() as uow:
            require(
                not uow.reviews.exists(case.review_case_id),
                f"case {case.review_case_id!r} already exists",
            )
            require(
                uow.reviews.get_open_by_candidate_fact(case.candidate_fact_id) is None,
                f"open case already exists for candidate_fact {case.candidate_fact_id!r}",
            )
            uow.reviews.save(case)
            uow.commit()

        return case

    def assign_case(
        self,
        case_id: ReviewCaseId,
        reviewer: UserId,
    ) -> ReviewCase:
        require(is_valid_review_case_id(case_id), "invalid case_id")
        require(is_valid_user_id(reviewer), "invalid reviewer")

        with self._uow_factory() as uow:
            case = uow.reviews.get(case_id)
            require(case is not None, f"case {case_id!r} not found")
            assert case is not None
            require(case.is_open, f"case {case_id!r} is not open")

            assigned = case.assign(reviewer)
            uow.reviews.save(assigned)
            uow.commit()

        return assigned

    def start_review(self, case_id: ReviewCaseId) -> ReviewCase:
        require(is_valid_review_case_id(case_id), "invalid case_id")

        with self._uow_factory() as uow:
            case = uow.reviews.get(case_id)
            require(case is not None, f"case {case_id!r} not found")
            assert case is not None

            started = case.start_review()
            uow.reviews.save(started)
            uow.commit()

        return started

    def decide(
        self,
        case_id: ReviewCaseId,
        outcome: ReviewOutcome,
        decided_by: UserId,
        rationale: str,
    ) -> tuple[ReviewCase, ReviewDecision]:
        require(is_valid_review_case_id(case_id), "invalid case_id")
        require(isinstance(outcome, ReviewOutcome), "invalid outcome")
        require(is_valid_user_id(decided_by), "invalid decided_by")
        require(
            isinstance(rationale, str) and bool(rationale.strip()),
            "rationale must not be blank",
        )

        with self._uow_factory() as uow:
            case = uow.reviews.get(case_id)
            require(case is not None, f"case {case_id!r} not found")
            assert case is not None
            require(
                case.status is ReviewStatus.IN_REVIEW,
                f"case {case_id!r} must be IN_REVIEW to decide",
            )
            require(
                uow.decisions.get_by_case(case_id) is None,
                f"decision already exists for case {case_id!r}",
            )

            updated = (
                case.escalate()
                if outcome is ReviewOutcome.ESCALATED
                else case.complete()
            )

            decision = ReviewDecision.create(
                review_id=case_id,
                decided_by=decided_by,
                decided_at=utcnow_iso(),
                outcome=outcome,
                rationale=rationale,
            )

            uow.reviews.save(updated)
            uow.decisions.save(decision)
            uow.commit()

        return updated, decision

    def cancel_case(
        self,
        case_id: ReviewCaseId,
        cancelled_by: UserId,
    ) -> ReviewCase:
        require(is_valid_review_case_id(case_id), "invalid case_id")
        require(is_valid_user_id(cancelled_by), "invalid cancelled_by")

        with self._uow_factory() as uow:
            case = uow.reviews.get(case_id)
            require(case is not None, f"case {case_id!r} not found")
            assert case is not None
            require(case.is_open, f"case {case_id!r} is not open")

            cancelled = case.cancel()
            uow.reviews.save(cancelled)
            uow.commit()

        return cancelled

    def get_case(self, case_id: ReviewCaseId) -> ReviewCase | None:
        require(is_valid_review_case_id(case_id), "invalid case_id")
        with self._uow_factory() as uow:
            return uow.reviews.get(case_id)

    def get_decision(self, case_id: ReviewCaseId) -> ReviewDecision | None:
        require(is_valid_review_case_id(case_id), "invalid case_id")
        with self._uow_factory() as uow:
            return uow.decisions.get_by_case(case_id)

    def list_by_entity(self, entity_id: EntityId) -> tuple[ReviewCase, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        with self._uow_factory() as uow:
            return uow.reviews.list_by_entity(entity_id)

    def list_by_status(self, status: ReviewStatus) -> tuple[ReviewCase, ...]:
        require(isinstance(status, ReviewStatus), "invalid status")
        with self._uow_factory() as uow:
            return uow.reviews.list_by_status(status)

    def list_by_assignee(self, user_id: UserId) -> tuple[ReviewCase, ...]:
        require(is_valid_user_id(user_id), "invalid user_id")
        with self._uow_factory() as uow:
            return uow.reviews.list_by_assignee(user_id)

    def list_by_priority(self, priority: ReviewPriority) -> tuple[ReviewCase, ...]:
        require(isinstance(priority, ReviewPriority), "invalid priority")
        with self._uow_factory() as uow:
            return uow.reviews.list_by_priority(priority)
