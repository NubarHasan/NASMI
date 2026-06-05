from __future__ import annotations

from typing import Protocol

from application.ports.conflict_repository import ConflictRepository
from application.ports.fact_repository import FactRepository
from application.ports.review_decision_repository import ReviewDecisionRepository
from application.ports.review_repository import ReviewRepository


class ReviewUnitOfWork(Protocol):

    reviews: ReviewRepository
    decisions: ReviewDecisionRepository
    facts: FactRepository
    conflicts: ConflictRepository

    def __enter__(self) -> ReviewUnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
