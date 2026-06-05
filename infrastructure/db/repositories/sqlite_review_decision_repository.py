from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from application.ports.review_decision_repository import ReviewDecisionRepository
from core.types import ReviewCaseId, ReviewDecisionId
from review.review_decision import ReviewDecision
from review.review_type import ReviewOutcome

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection


_INSERT = """
INSERT INTO review_decisions (
    decision_id,
    review_id,
    decided_by,
    decided_at,
    outcome,
    rationale,
    metadata
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""

_SELECT_BY_ID = """
SELECT decision_id, review_id, decided_by, decided_at,
       outcome, rationale, metadata
FROM review_decisions
WHERE decision_id = ?
"""

_SELECT_LATEST_BY_CASE = """
SELECT decision_id, review_id, decided_by, decided_at,
       outcome, rationale, metadata
FROM review_decisions
WHERE review_id = ?
ORDER BY decided_at DESC
LIMIT 1
"""

_SELECT_BY_OUTCOME = """
SELECT decision_id, review_id, decided_by, decided_at,
       outcome, rationale, metadata
FROM review_decisions
WHERE outcome = ?
ORDER BY decided_at ASC
"""

_EXISTS = "SELECT 1 FROM review_decisions WHERE decision_id = ? LIMIT 1"


def _row_to_decision(row: sqlite3.Row) -> ReviewDecision:
    return ReviewDecision(
        decision_id=ReviewDecisionId(row["decision_id"]),
        review_id=ReviewCaseId(row["review_id"]),
        decided_by=row["decided_by"],
        decided_at=row["decided_at"],
        outcome=ReviewOutcome(row["outcome"]),
        rationale=row["rationale"],
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
    )


def _decision_to_params(d: ReviewDecision) -> tuple[str, ...]:
    return (
        d.decision_id,
        d.review_id,
        d.decided_by,
        d.decided_at,
        d.outcome.value,
        d.rationale,
        json.dumps(d.metadata, ensure_ascii=False),
    )


class SqliteReviewDecisionRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, decision: ReviewDecision) -> None:
        self._conn.execute(_INSERT, _decision_to_params(decision))

    def get(self, decision_id: ReviewDecisionId) -> ReviewDecision | None:
        row = self._conn.execute(_SELECT_BY_ID, (decision_id,)).fetchone()
        return _row_to_decision(row) if row else None

    def exists(self, decision_id: ReviewDecisionId) -> bool:
        row = self._conn.execute(_EXISTS, (decision_id,)).fetchone()
        return row is not None

    def get_by_case(self, review_id: ReviewCaseId) -> ReviewDecision | None:
        row = self._conn.execute(_SELECT_LATEST_BY_CASE, (review_id,)).fetchone()
        return _row_to_decision(row) if row else None

    def list_by_outcome(
        self,
        outcome: ReviewOutcome,
    ) -> tuple[ReviewDecision, ...]:
        rows = self._conn.execute(_SELECT_BY_OUTCOME, (outcome.value,)).fetchall()
        return tuple(_row_to_decision(r) for r in rows)


def _assert_protocol() -> None:
    _: ReviewDecisionRepository = SqliteReviewDecisionRepository.__new__(
        SqliteReviewDecisionRepository
    )


_assert_protocol()
