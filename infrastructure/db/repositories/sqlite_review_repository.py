from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from application.ports.review_repository import ReviewRepository
from core.types import (
    CandidateFactId,
    EntityId,
    EvidenceId,
    ReviewCaseId,
    UserId,
)
from review.review_case import ReviewCase
from review.review_type import ReviewPriority, ReviewStatus

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection


_INSERT_OR_REPLACE = """
INSERT INTO review_cases (
    review_case_id,
    entity_id,
    candidate_fact_id,
    fact_type,
    raw_value,
    normalized_value,
    confidence,
    evidence_ids,
    status,
    priority,
    created_at,
    assigned_to,
    metadata
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(review_case_id) DO UPDATE SET
    status      = excluded.status,
    priority    = excluded.priority,
    assigned_to = excluded.assigned_to,
    metadata    = excluded.metadata
"""

_SELECT_BY_ID = """
SELECT
    review_case_id, entity_id, candidate_fact_id, fact_type,
    raw_value, normalized_value, confidence, evidence_ids,
    status, priority, created_at, assigned_to, metadata
FROM review_cases
WHERE review_case_id = ?
"""

_EXISTS_BY_ID = "SELECT 1 FROM review_cases WHERE review_case_id = ? LIMIT 1"

_SELECT_OPEN_BY_CANDIDATE = """
SELECT
    review_case_id, entity_id, candidate_fact_id, fact_type,
    raw_value, normalized_value, confidence, evidence_ids,
    status, priority, created_at, assigned_to, metadata
FROM review_cases
WHERE candidate_fact_id = ?
  AND status NOT IN ('COMPLETED', 'CANCELLED')
LIMIT 1
"""

_LIST_BY_ENTITY = """
SELECT
    review_case_id, entity_id, candidate_fact_id, fact_type,
    raw_value, normalized_value, confidence, evidence_ids,
    status, priority, created_at, assigned_to, metadata
FROM review_cases
WHERE entity_id = ?
ORDER BY created_at ASC
"""

_LIST_BY_STATUS = """
SELECT
    review_case_id, entity_id, candidate_fact_id, fact_type,
    raw_value, normalized_value, confidence, evidence_ids,
    status, priority, created_at, assigned_to, metadata
FROM review_cases
WHERE status = ?
ORDER BY created_at ASC
"""

_LIST_BY_ASSIGNEE = """
SELECT
    review_case_id, entity_id, candidate_fact_id, fact_type,
    raw_value, normalized_value, confidence, evidence_ids,
    status, priority, created_at, assigned_to, metadata
FROM review_cases
WHERE assigned_to = ?
ORDER BY created_at ASC
"""

_LIST_BY_PRIORITY = """
SELECT
    review_case_id, entity_id, candidate_fact_id, fact_type,
    raw_value, normalized_value, confidence, evidence_ids,
    status, priority, created_at, assigned_to, metadata
FROM review_cases
WHERE priority = ?
ORDER BY created_at ASC
"""


def _row_to_review_case(row: sqlite3.Row) -> ReviewCase:
    return ReviewCase(
        review_case_id=ReviewCaseId(row["review_case_id"]),
        entity_id=EntityId(row["entity_id"]),
        candidate_fact_id=CandidateFactId(row["candidate_fact_id"]),
        fact_type=row["fact_type"],
        raw_value=row["raw_value"],
        normalized_value=row["normalized_value"],
        confidence=float(row["confidence"]),
        evidence_ids=tuple(EvidenceId(v) for v in json.loads(row["evidence_ids"])),
        status=ReviewStatus(row["status"]),
        priority=ReviewPriority(row["priority"]),
        created_at=row["created_at"],
        assigned_to=UserId(row["assigned_to"]) if row["assigned_to"] else None,
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
    )


def _case_to_params(case: ReviewCase) -> tuple[str | float | None, ...]:
    return (
        case.review_case_id,
        case.entity_id,
        case.candidate_fact_id,
        case.fact_type,
        case.raw_value,
        case.normalized_value,
        case.confidence,
        json.dumps(list(case.evidence_ids), ensure_ascii=False),
        case.status.value,
        case.priority.value,
        case.created_at,
        case.assigned_to,
        json.dumps(case.metadata, ensure_ascii=False),
    )


class SqliteReviewRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, case: ReviewCase) -> None:
        self._conn.execute(_INSERT_OR_REPLACE, _case_to_params(case))

    def get(self, case_id: ReviewCaseId) -> ReviewCase | None:
        row = self._conn.execute(_SELECT_BY_ID, (case_id,)).fetchone()
        return _row_to_review_case(row) if row else None

    def exists(self, case_id: ReviewCaseId) -> bool:
        row = self._conn.execute(_EXISTS_BY_ID, (case_id,)).fetchone()
        return row is not None

    def get_open_by_candidate_fact(
        self,
        candidate_fact_id: str,
    ) -> ReviewCase | None:
        row = self._conn.execute(
            _SELECT_OPEN_BY_CANDIDATE, (candidate_fact_id,)
        ).fetchone()
        return _row_to_review_case(row) if row else None

    def list_by_entity(self, entity_id: EntityId) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_ENTITY, (entity_id,)).fetchall()
        return tuple(_row_to_review_case(r) for r in rows)

    def list_by_status(self, status: ReviewStatus) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_STATUS, (status.value,)).fetchall()
        return tuple(_row_to_review_case(r) for r in rows)

    def list_by_assignee(self, user_id: UserId) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_ASSIGNEE, (user_id,)).fetchall()
        return tuple(_row_to_review_case(r) for r in rows)

    def list_by_priority(self, priority: ReviewPriority) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_PRIORITY, (priority.value,)).fetchall()
        return tuple(_row_to_review_case(r) for r in rows)


def _assert_protocol() -> None:
    _: ReviewRepository = SqliteReviewRepository.__new__(SqliteReviewRepository)


_assert_protocol()
