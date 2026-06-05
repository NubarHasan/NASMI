from __future__ import annotations

import json
import sqlite3

from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from knowledge.conflict import Conflict, ConflictStatus

_SELECT_CONFLICT = """
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
            "fact_ids": json.loads(row["fact_ids"] or "[]"),
            "status": row["status"],
            "created_at": row["created_at"],
            "resolved_fact_id": row["resolved_fact_id"],
            "resolution_note": row["resolution_note"] or "",
            "resolved_by": row["resolved_by"],
            "resolved_at": row["resolved_at"],
        }
    )


class SqliteConflictQuery:
    """
    Read-only implementation of ConflictQueryService.

    - Never mutates conflict records.
    - Returns an empty tuple when no conflicts exist.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def list_conflicts(
        self,
        entity_id: EntityId,
    ) -> tuple[Conflict, ...]:
        """Return all conflicts linked to the given entity."""
        cursor = self._db.connection.execute(
            _SELECT_CONFLICT + """
            WHERE entity_id = ?
            ORDER BY created_at ASC
            """,
            (str(entity_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_conflict(row) for row in rows)

    def list_conflicts_by_status(
        self,
        entity_id: EntityId,
        status: ConflictStatus,
    ) -> tuple[Conflict, ...]:
        """Return conflicts filtered by status for the given entity."""
        cursor = self._db.connection.execute(
            _SELECT_CONFLICT + """
            WHERE entity_id = ?
              AND status = ?
            ORDER BY created_at ASC
            """,
            (str(entity_id), str(status)),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_conflict(row) for row in rows)
