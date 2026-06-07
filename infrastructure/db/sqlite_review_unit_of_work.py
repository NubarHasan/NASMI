from __future__ import annotations

from application.ports.conflict_repository import ConflictRepository
from application.ports.fact_repository import FactRepository
from application.ports.review_decision_repository import ReviewDecisionRepository
from application.ports.review_repository import ReviewRepository
from application.ports.review_unit_of_work import ReviewUnitOfWork
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.repositories.sqlite_conflict_repository import (
    SqliteConflictRepository,
)
from infrastructure.db.repositories.sqlite_fact_repository import SqliteFactRepository
from infrastructure.db.repositories.sqlite_review_decision_repository import (
    SqliteReviewDecisionRepository,
)
from infrastructure.db.repositories.sqlite_review_repository import (
    SqliteReviewRepository,
)


class SqliteReviewUnitOfWork:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self.reviews: ReviewRepository = SqliteReviewRepository(db)
        self.decisions: ReviewDecisionRepository = SqliteReviewDecisionRepository(db)
        self.facts: FactRepository = SqliteFactRepository(db)
        self.conflicts: ConflictRepository = SqliteConflictRepository(db)

    def __enter__(self) -> ReviewUnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self._db.connection.commit()

    def rollback(self) -> None:
        self._db.connection.rollback()
