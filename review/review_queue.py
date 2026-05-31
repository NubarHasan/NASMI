from __future__ import annotations

from dataclasses import dataclass

from core.guards import require
from core.identifiers import generate_review_queue_id, is_valid_review_queue_id
from core.time import parse_timestamp
from core.types import ReviewCaseId, ReviewQueueId
from review.review_case import ReviewCase
from review.review_type import ReviewPriority, ReviewStatus

_PRIORITY_ORDER: dict[ReviewPriority, int] = {
    ReviewPriority.CRITICAL: 0,
    ReviewPriority.HIGH: 1,
    ReviewPriority.NORMAL: 2,
    ReviewPriority.LOW: 3,
}


@dataclass(frozen=True)
class ReviewQueue:
    queue_id: ReviewQueueId
    cases: tuple[ReviewCase, ...]

    def __post_init__(self) -> None:
        require(
            is_valid_review_queue_id(self.queue_id),
            f"Invalid ReviewQueueId: [{self.queue_id}]",
        )

    def _sorted(self, cases: tuple[ReviewCase, ...]) -> tuple[ReviewCase, ...]:
        return tuple(
            sorted(
                cases,
                key=lambda c: (
                    _PRIORITY_ORDER[c.priority],
                    parse_timestamp(c.created_at),
                ),
            )
        )

    def enqueue(self, case: ReviewCase) -> ReviewQueue:
        existing_ids = {c.review_id for c in self.cases}
        require(
            case.review_id not in existing_ids,
            f"ReviewCase [{case.review_id}] is already in queue [{self.queue_id}]",
        )
        return ReviewQueue(
            queue_id=self.queue_id,
            cases=self._sorted(self.cases + (case,)),
        )

    def dequeue(self) -> tuple[ReviewCase, ReviewQueue]:
        require(len(self.cases) > 0, f"Queue [{self.queue_id}] is empty")
        return self.cases[0], ReviewQueue(
            queue_id=self.queue_id,
            cases=self.cases[1:],
        )

    def remove(self, review_id: ReviewCaseId) -> ReviewQueue:
        remaining = tuple(c for c in self.cases if c.review_id != review_id)
        require(
            len(remaining) < len(self.cases),
            f"ReviewCase [{review_id}] not found in queue [{self.queue_id}]",
        )
        return ReviewQueue(queue_id=self.queue_id, cases=remaining)

    def update(self, updated_case: ReviewCase) -> ReviewQueue:
        require(
            any(c.review_id == updated_case.review_id for c in self.cases),
            f"ReviewCase [{updated_case.review_id}] not found in queue [{self.queue_id}]",
        )
        updated = tuple(
            updated_case if c.review_id == updated_case.review_id else c
            for c in self.cases
        )
        return ReviewQueue(queue_id=self.queue_id, cases=self._sorted(updated))

    def peek(self) -> ReviewCase | None:
        return self.cases[0] if self.cases else None

    def by_priority(self, priority: ReviewPriority) -> ReviewQueue:
        return ReviewQueue(
            queue_id=self.queue_id,
            cases=tuple(c for c in self.cases if c.priority == priority),
        )

    def by_entity(self, entity_id: str) -> tuple[ReviewCase, ...]:
        return tuple(c for c in self.cases if c.entity_id == entity_id)

    def pending(self) -> tuple[ReviewCase, ...]:
        return tuple(c for c in self.cases if c.status == ReviewStatus.PENDING)

    def escalated(self) -> tuple[ReviewCase, ...]:
        return tuple(c for c in self.cases if c.status == ReviewStatus.ESCALATED)

    def assigned_to(self, reviewer: str) -> tuple[ReviewCase, ...]:
        return tuple(c for c in self.cases if c.assigned_to == reviewer)

    def open_cases(self) -> tuple[ReviewCase, ...]:
        return tuple(c for c in self.cases if c.is_open)

    def critical(self) -> tuple[ReviewCase, ...]:
        return tuple(c for c in self.cases if c.priority == ReviewPriority.CRITICAL)

    @property
    def size(self) -> int:
        return len(self.cases)

    @property
    def is_empty(self) -> bool:
        return len(self.cases) == 0

    @classmethod
    def create(cls, queue_id: ReviewQueueId | None = None) -> ReviewQueue:
        return cls(
            queue_id=queue_id if queue_id is not None else generate_review_queue_id(),
            cases=(),
        )
