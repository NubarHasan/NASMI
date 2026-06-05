from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from application.ports.conflict_repository import ConflictRepository
from core.types import ConflictId, EntityId, FactId
from knowledge.conflict import Conflict, ConflictStatus

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection


_INSERT_OR_REPLACE = """
INSERT INTO conflicts (
    conflict_id,
    entity_id,
    field_name,
    fact_ids,
    status,
    created_at,
    resolved_fact_id,
    resolution_note,
    resolved_by,
    resolved_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(conflict_id) DO UPDATE SET
    field_name       = excluded.field_name,
    fact_ids         = excluded.fact_ids,
    status           = excluded.status,
    resolved_fact_id = excluded.resolved_fact_id,
    resolution_note  = excluded.resolution_note,
    resolved_by      = excluded.resolved_by,
    resolved_at      = excluded.resolved_at
"""

_SELECT_BY_ID = """
SELECT
    conflict_id,
    entity_id,
    field_name,
    fact_ids,
    status,
    created_at,
    resolved_fact_id,
    resolution_note,
    resolved_by,
    resolved_at
FROM conflicts
WHERE conflict_id = ?
"""

_EXISTS_BY_ID = "SELECT 1 FROM conflicts WHERE conflict_id = ? LIMIT 1"

_LIST_BY_ENTITY = """
SELECT
    conflict_id,
    entity_id,
    field_name,
    fact_ids,
    status,
    created_at,
    resolved_fact_id,
    resolution_note,
    resolved_by,
    resolved_at
FROM conflicts
WHERE entity_id = ?
ORDER BY created_at ASC
"""

_LIST_BY_STATUS = """
SELECT
    conflict_id,
    entity_id,
    field_name,
    fact_ids,
    status,
    created_at,
    resolved_fact_id,
    resolution_note,
    resolved_by,
    resolved_at
FROM conflicts
WHERE entity_id = ?
  AND status    = ?
ORDER BY created_at ASC
"""

_OPEN_FACT_IDS = "SELECT fact_ids FROM conflicts WHERE status = 'open'"

_LIST_BY_FACT = """
SELECT
    conflict_id,
    entity_id,
    field_name,
    fact_ids,
    status,
    created_at,
    resolved_fact_id,
    resolution_note,
    resolved_by,
    resolved_at
FROM conflicts
"""


def _row_to_conflict(row: sqlite3.Row) -> Conflict:
    return Conflict.from_dict(
        {
            "conflict_id": row["conflict_id"],
            "entity_id": row["entity_id"],
            "field_name": row["field_name"],
            "fact_ids": json.loads(row["fact_ids"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "resolved_fact_id": row["resolved_fact_id"],
            "resolution_note": row["resolution_note"] or "",
            "resolved_by": row["resolved_by"],
            "resolved_at": row["resolved_at"],
        }
    )


def _conflict_to_params(conflict: Conflict) -> tuple[str | None, ...]:
    d = conflict.to_dict()
    return (
        d["conflict_id"],
        d["entity_id"],
        d["field_name"],
        json.dumps(d["fact_ids"], ensure_ascii=False),
        d["status"],
        d["created_at"],
        d["resolved_fact_id"],
        d["resolution_note"],
        d["resolved_by"],
        d["resolved_at"],
    )


class SqliteConflictRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, conflict: Conflict) -> None:
        self._conn.execute(_INSERT_OR_REPLACE, _conflict_to_params(conflict))

    def get(self, conflict_id: ConflictId) -> Conflict | None:
        row = self._conn.execute(_SELECT_BY_ID, (conflict_id,)).fetchone()
        return _row_to_conflict(row) if row else None

    def exists(self, conflict_id: ConflictId) -> bool:
        row = self._conn.execute(_EXISTS_BY_ID, (conflict_id,)).fetchone()
        return row is not None

    def exists_for_facts(self, fact_ids: tuple[FactId, ...]) -> bool:
        target = set(fact_ids)
        for (fact_ids_json,) in self._conn.execute(_OPEN_FACT_IDS):
            if set(json.loads(fact_ids_json)) == target:
                return True
        return False

    def list_by_entity(self, entity_id: EntityId) -> tuple[Conflict, ...]:
        rows = self._conn.execute(_LIST_BY_ENTITY, (entity_id,)).fetchall()
        return tuple(_row_to_conflict(r) for r in rows)

    def list_by_fact(self, fact_id: FactId) -> tuple[Conflict, ...]:
        result: list[Conflict] = []
        for row in self._conn.execute(_LIST_BY_FACT):
            if fact_id in json.loads(row["fact_ids"]):
                result.append(_row_to_conflict(row))
        return tuple(result)

    def list_by_status(
        self,
        entity_id: EntityId,
        status: ConflictStatus,
    ) -> tuple[Conflict, ...]:
        rows = self._conn.execute(_LIST_BY_STATUS, (entity_id, str(status))).fetchall()
        return tuple(_row_to_conflict(r) for r in rows)


def _assert_protocol() -> None:
    _: ConflictRepository = SqliteConflictRepository.__new__(SqliteConflictRepository)


_assert_protocol()
