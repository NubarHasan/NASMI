from __future__ import annotations

import json
import sqlite3

from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from knowledge.fact import Fact, FactStatus


def _row_to_fact(row: sqlite3.Row) -> Fact:
    return Fact.from_dict(
        {
            "fact_id": row["fact_id"],
            "entity_id": row["entity_id"],
            "field_name": row["field_name"],
            "canonical_value": row["canonical_value"],
            "display_value": row["display_value"],
            "value_type": row["value_type"],
            "confidence": row["confidence"],
            "status": row["status"],
            "source_stage": row["source_stage"],
            "created_at": row["created_at"],
            "accepted_at": row["accepted_at"],
            "accepted_by": row["accepted_by"],
            "superseded_by": row["superseded_by"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
    )


class SqliteKnowledgeQuery:
    """
    Read-only implementation of KnowledgeQueryService.

    - Returns only FactStatus.ACCEPTED facts.
    - Never mutates knowledge records.
    - Returns an empty tuple when no facts exist for entity_id.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def list_accepted_facts(
        self,
        entity_id: EntityId,
    ) -> tuple[Fact, ...]:
        cursor = self._db.connection.execute(
            """
            SELECT
                fact_id,
                entity_id,
                field_name,
                canonical_value,
                display_value,
                value_type,
                confidence,
                status,
                source_stage,
                created_at,
                accepted_at,
                accepted_by,
                superseded_by,
                metadata
            FROM facts
            WHERE entity_id = ?
              AND status = ?
            ORDER BY created_at ASC
            """,
            (str(entity_id), FactStatus.ACCEPTED.value),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_fact(row) for row in rows)
