from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from core.guards import require
from core.identifiers import (
    is_valid_candidate_fact_id,
    is_valid_entity_id,
    is_valid_review_case_id,
    is_valid_user_id,
)
from core.time import utcnow_iso
from core.types import (
    CandidateFactId,
    ConfidenceScore,
    EntityId,
    EvidenceId,
    ReviewCaseId,
    UserId,
)
from review.review_case import ReviewCase
from review.review_decision import ReviewDecision
from review.review_queue import ReviewQueue
from review.review_type import ReviewOutcome, ReviewPriority, ReviewStatus

_SYSTEM_ACTOR: Final[str] = "system"
_AUTO_REVIEW_CONFIDENCE_THRESHOLD: Final[float] = 0.75


@dataclass
class _ReviewStore:
    _cases: dict[ReviewCaseId, ReviewCase] = field(default_factory=dict)
    _decisions: dict[ReviewCaseId, list[ReviewDecision]] = field(default_factory=dict)
    _queue: ReviewQueue = field(
        default_factory=ReviewQueue.create,
    )


class ReviewService:

    def __init__(self) -> None:
        self._store = _ReviewStore()

    def open_case(
        self,
        entity_id: EntityId,
        candidate_fact_id: CandidateFactId,
        fact_type: str,
        raw_value: str,
        normalized_value: str,
        confidence: ConfidenceScore,
        evidence_ids: tuple[EvidenceId, ...],
        priority: ReviewPriority = ReviewPriority.NORMAL,
    ) -> ReviewCase:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(
            is_valid_candidate_fact_id(candidate_fact_id),
            "invalid candidate_fact_id",
        )
        require(bool(fact_type.strip()), "fact_type must not be blank")
        require(bool(raw_value.strip()), "raw_value must not be blank")
        require(bool(normalized_value.strip()), "normalized_value must not be blank")
        require(
            0.0 <= confidence <= 1.0,
            f"confidence must be between 0.0 and 1.0, got [{confidence}]",
        )
        require(
            isinstance(evidence_ids, tuple),
            "evidence_ids must be a tuple",
        )
        require(len(evidence_ids) > 0, "evidence_ids must not be empty")

        case = ReviewCase.create(
            entity_id=entity_id,
            candidate_fact_id=candidate_fact_id,
            fact_type=fact_type,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=confidence,
            evidence_ids=evidence_ids,
            priority=priority,
        )

        self._store._cases[case.review_case_id] = case
        self._store._queue = self._store._queue.enqueue(case)
        return case

    def needs_review(self, confidence: ConfidenceScore) -> bool:
        require(
            0.0 <= confidence <= 1.0,
            f"confidence must be between 0.0 and 1.0, got [{confidence}]",
        )
        return confidence < _AUTO_REVIEW_CONFIDENCE_THRESHOLD

    def get_case(self, review_case_id: ReviewCaseId) -> ReviewCase | None:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")
        return self._store._cases.get(review_case_id)

    def list_cases(self, entity_id: EntityId) -> tuple[ReviewCase, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(c for c in self._store._cases.values() if c.entity_id == entity_id)

    def list_open_cases(self, entity_id: EntityId) -> tuple[ReviewCase, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(
            c
            for c in self._store._cases.values()
            if c.entity_id == entity_id and c.is_open
        )

    def assign_case(
        self,
        review_case_id: ReviewCaseId,
        reviewer: UserId,
    ) -> ReviewCase:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")
        require(is_valid_user_id(reviewer), "invalid reviewer UserId")

        case = self._store._cases.get(review_case_id)
        require(case is not None, f"ReviewCase [{review_case_id}] not found")
        assert case is not None

        require(case.is_open, f"ReviewCase [{review_case_id}] is not open")

        updated = case.assign(reviewer)
        self._store._cases[review_case_id] = updated
        self._store._queue = self._store._queue.update(updated)
        return updated

    def start_review(self, review_case_id: ReviewCaseId) -> ReviewCase:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")

        case = self._store._cases.get(review_case_id)
        require(case is not None, f"ReviewCase [{review_case_id}] not found")
        assert case is not None

        updated = case.start_review()
        self._store._cases[review_case_id] = updated
        self._store._queue = self._store._queue.update(updated)
        return updated

    def submit_decision(
        self,
        review_case_id: ReviewCaseId,
        decided_by: str,
        outcome: ReviewOutcome,
        rationale: str,
    ) -> ReviewDecision | ReviewCase:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")
        require(bool(decided_by.strip()), "decided_by must not be blank")
        require(bool(rationale.strip()), "rationale must not be blank")

        case = self._store._cases.get(review_case_id)
        require(case is not None, f"ReviewCase [{review_case_id}] not found")
        assert case is not None

        require(
            case.status == ReviewStatus.IN_REVIEW,
            f"ReviewCase [{review_case_id}] must be IN_REVIEW to submit a decision",
        )

        if outcome == ReviewOutcome.ESCALATED:
            escalated = case.escalate()
            self._store._cases[review_case_id] = escalated
            self._store._queue = self._store._queue.update(escalated)
            return escalated

        decision = ReviewDecision.create(
            review_id=review_case_id,
            decided_by=decided_by,
            decided_at=utcnow_iso(),
            outcome=outcome,
            rationale=rationale,
        )

        decisions = self._store._decisions.setdefault(review_case_id, [])
        decisions.append(decision)

        completed = case.complete()
        self._store._cases[review_case_id] = completed
        self._store._queue = self._store._queue.update(completed)
        return decision

    def get_decision(self, review_case_id: ReviewCaseId) -> ReviewDecision | None:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")
        decisions = self._store._decisions.get(review_case_id)
        return decisions[-1] if decisions else None

    def list_decisions(
        self,
        review_case_id: ReviewCaseId,
    ) -> tuple[ReviewDecision, ...]:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")
        return tuple(self._store._decisions.get(review_case_id, []))

    def cancel_case(
        self,
        review_case_id: ReviewCaseId,
        cancelled_by: str = _SYSTEM_ACTOR,
    ) -> ReviewCase:
        require(is_valid_review_case_id(review_case_id), "invalid review_case_id")
        require(bool(cancelled_by.strip()), "cancelled_by must not be blank")

        case = self._store._cases.get(review_case_id)
        require(case is not None, f"ReviewCase [{review_case_id}] not found")
        assert case is not None

        updated = case.cancel()
        self._store._cases[review_case_id] = updated
        self._store._queue = self._store._queue.remove(review_case_id)
        return updated

    def peek_queue(self) -> ReviewCase | None:
        return self._store._queue.peek()

    def dequeue_next(self) -> ReviewCase | None:
        if self._store._queue.is_empty:
            return None
        case, updated_queue = self._store._queue.dequeue()
        self._store._queue = updated_queue
        return case

    def queue_size(self) -> int:
        return self._store._queue.size

    def pending_cases(self) -> tuple[ReviewCase, ...]:
        return self._store._queue.pending()

    def critical_cases(self) -> tuple[ReviewCase, ...]:
        return self._store._queue.critical()

    def cases_by_entity(self, entity_id: EntityId) -> tuple[ReviewCase, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return self._store._queue.by_entity(entity_id)

    def cases_assigned_to(self, reviewer: UserId) -> tuple[ReviewCase, ...]:
        require(is_valid_user_id(reviewer), "invalid reviewer UserId")
        return self._store._queue.assigned_to(reviewer)
