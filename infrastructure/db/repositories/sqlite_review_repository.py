from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, cast

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
    entity_id = excluded.entity_id,
    candidate_fact_id = excluded.candidate_fact_id,
    fact_type = excluded.fact_type,
    raw_value = excluded.raw_value,
    normalized_value = excluded.normalized_value,
    confidence = excluded.confidence,
    evidence_ids = excluded.evidence_ids,
    status = excluded.status,
    priority = excluded.priority,
    assigned_to = excluded.assigned_to,
    metadata = excluded.metadata
"""

_SELECT_BY_ID = """
SELECT
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
FROM review_cases
WHERE review_case_id = ?
"""

_EXISTS_BY_ID = """
SELECT 1
FROM review_cases
WHERE review_case_id = ?
LIMIT 1
"""

_SELECT_OPEN_BY_CANDIDATE = """
SELECT
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
FROM review_cases
WHERE candidate_fact_id = ?
  AND UPPER(status) NOT IN ('COMPLETED', 'CANCELLED', 'ACCEPTED', 'REJECTED')
LIMIT 1
"""

_LIST_BY_ENTITY = """
SELECT
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
FROM review_cases
WHERE entity_id = ?
ORDER BY created_at ASC
"""

_LIST_BY_STATUS = """
SELECT
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
FROM review_cases
WHERE UPPER(status) = UPPER(?)
ORDER BY created_at ASC
"""

_LIST_BY_ASSIGNEE = """
SELECT
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
FROM review_cases
WHERE assigned_to = ?
ORDER BY created_at ASC
"""

_LIST_BY_PRIORITY = """
SELECT
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
FROM review_cases
WHERE UPPER(priority) = UPPER(?)
ORDER BY created_at ASC
"""


def _safe_json_list(value: object) -> list[str]:
    if not value:
        return []

    try:
        loaded = json.loads(str(value))
    except Exception:
        return []

    if not isinstance(loaded, list):
        return []

    return [str(item) for item in loaded]


def _safe_json_dict(value: object) -> dict[str, object]:
    if not value:
        return {}

    try:
        loaded = json.loads(str(value))
    except Exception:
        return {}

    if not isinstance(loaded, dict):
        return {}

    return {str(key): val for key, val in loaded.items()}


def _parse_status(value: object) -> ReviewStatus:
    raw = str(value or "").strip()
    raw_upper = raw.upper()

    for status in ReviewStatus:
        status_value = str(status.value)
        status_name = str(status.name)

        if (
            raw == status_value
            or raw_upper == status_value.upper()
            or raw_upper == status_name.upper()
        ):
            return status

    return ReviewStatus.PENDING


def _first_review_priority() -> ReviewPriority:
    priorities = list(ReviewPriority)
    if priorities:
        return cast(ReviewPriority, priorities[0])

    raise ValueError("ReviewPriority enum has no values")


def _parse_priority(value: object) -> ReviewPriority:
    raw = str(value or "").strip()
    raw_upper = raw.upper()

    for priority in ReviewPriority:
        priority_value = str(priority.value)
        priority_name = str(priority.name)

        if (
            raw == priority_value
            or raw_upper == priority_value.upper()
            or raw_upper == priority_name.upper()
        ):
            return priority

    return _first_review_priority()


def _row_to_review_case(row: sqlite3.Row) -> ReviewCase:
    return ReviewCase(
        review_case_id=ReviewCaseId(str(row["review_case_id"])),
        entity_id=EntityId(str(row["entity_id"])),
        candidate_fact_id=CandidateFactId(str(row["candidate_fact_id"])),
        fact_type=str(row["fact_type"] or ""),
        raw_value=str(row["raw_value"] or ""),
        normalized_value=str(row["normalized_value"] or ""),
        confidence=float(row["confidence"] or 0.0),
        evidence_ids=tuple(
            EvidenceId(item) for item in _safe_json_list(row["evidence_ids"])
        ),
        status=_parse_status(row["status"]),
        priority=_parse_priority(row["priority"]),
        created_at=str(row["created_at"]),
        assigned_to=UserId(str(row["assigned_to"])) if row["assigned_to"] else None,
        metadata=_safe_json_dict(row["metadata"]),
    )


def _case_to_params(case: ReviewCase) -> tuple[object, ...]:
    return (
        str(case.review_case_id),
        str(case.entity_id),
        str(case.candidate_fact_id),
        str(case.fact_type),
        str(case.raw_value or ""),
        str(case.normalized_value or ""),
        float(case.confidence or 0.0),
        json.dumps([str(item) for item in case.evidence_ids], ensure_ascii=False),
        str(case.status.value).upper(),
        str(case.priority.value).upper(),
        str(case.created_at),
        str(case.assigned_to) if case.assigned_to else None,
        json.dumps(dict(case.metadata or {}), ensure_ascii=False),
    )


class SqliteReviewRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, case: ReviewCase) -> None:
        self._conn.execute(_INSERT_OR_REPLACE, _case_to_params(case))
        self._conn.commit()

    def get(self, case_id: ReviewCaseId) -> ReviewCase | None:
        row = self._conn.execute(_SELECT_BY_ID, (str(case_id),)).fetchone()
        return _row_to_review_case(row) if row else None

    def exists(self, case_id: ReviewCaseId) -> bool:
        row = self._conn.execute(_EXISTS_BY_ID, (str(case_id),)).fetchone()
        return row is not None

    def get_open_by_candidate_fact(
        self,
        candidate_fact_id: str,
    ) -> ReviewCase | None:
        row = self._conn.execute(
            _SELECT_OPEN_BY_CANDIDATE,
            (str(candidate_fact_id),),
        ).fetchone()
        return _row_to_review_case(row) if row else None

    def list_by_entity(self, entity_id: EntityId) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_ENTITY, (str(entity_id),)).fetchall()
        return tuple(_row_to_review_case(row) for row in rows)

    def list_by_status(self, status: ReviewStatus) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_STATUS, (str(status.value),)).fetchall()
        return tuple(_row_to_review_case(row) for row in rows)

    def list_by_assignee(self, user_id: UserId) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_ASSIGNEE, (str(user_id),)).fetchall()
        return tuple(_row_to_review_case(row) for row in rows)

    def list_by_priority(self, priority: ReviewPriority) -> tuple[ReviewCase, ...]:
        rows = self._conn.execute(_LIST_BY_PRIORITY, (str(priority.value),)).fetchall()
        return tuple(_row_to_review_case(row) for row in rows)


def _assert_protocol() -> None:
    _: ReviewRepository = SqliteReviewRepository.__new__(SqliteReviewRepository)


_assert_protocol()
