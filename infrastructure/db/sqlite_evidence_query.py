from __future__ import annotations

import json
import sqlite3

from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from knowledge.evidence import Evidence


def _row_to_evidence(row: sqlite3.Row) -> Evidence:
    return Evidence.from_dict(
        {
            "evidence_id": row["evidence_id"],
            "source_id": row["source_id"],
            "entity_id": row["entity_id"],
            "field_name": row["field_name"],
            "raw_value": row["raw_value"],
            "extraction_method": row["extraction_method"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
            "location": json.loads(row["location"] or "{}"),
            "metadata": json.loads(row["metadata"] or "{}"),
        }
    )


class SqliteEvidenceQuery:
    """
    Read-only implementation of EvidenceQueryService.

    - Never mutates evidence records.
    - Returns an empty tuple when no evidence exists.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def list_evidence(
        self,
        entity_id: EntityId,
    ) -> tuple[Evidence, ...]:
        """Return all evidence items linked to the given entity."""
        cursor = self._db.connection.execute(
            """
            SELECT
                evidence_id,
                source_id,
                entity_id,
                field_name,
                raw_value,
                extraction_method,
                confidence,
                created_at,
                location,
                metadata
            FROM evidence
            WHERE entity_id = ?
            ORDER BY created_at ASC
            """,
            (str(entity_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_evidence(row) for row in rows)

    def list_evidence_for_field(
        self,
        entity_id: EntityId,
        field_name: str,
    ) -> tuple[Evidence, ...]:
        """Return evidence items linked to a specific field of the given entity."""
        cursor = self._db.connection.execute(
            """
            SELECT
                evidence_id,
                source_id,
                entity_id,
                field_name,
                raw_value,
                extraction_method,
                confidence,
                created_at,
                location,
                metadata
            FROM evidence
            WHERE entity_id = ?
              AND field_name = ?
            ORDER BY created_at ASC
            """,
            (str(entity_id), field_name),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_evidence(row) for row in rows)
