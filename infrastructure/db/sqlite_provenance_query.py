from __future__ import annotations

import json
import sqlite3

from core.types import EntityId, FactId
from infrastructure.db.connection import DatabaseConnection
from knowledge.provenance import Provenance

_SELECT_PROVENANCE = """
    SELECT
        provenance_id,
        fact_id,
        entity_id,
        decision_chain,
        summary,
        created_at
    FROM provenance
"""


def _row_to_provenance(row: sqlite3.Row) -> Provenance:
    return Provenance.from_dict(
        {
            "provenance_id": row["provenance_id"],
            "fact_id": row["fact_id"],
            "entity_id": row["entity_id"],
            "decision_chain": json.loads(row["decision_chain"] or "[]"),
            "summary": row["summary"],
            "created_at": row["created_at"],
        }
    )


class SqliteProvenanceQuery:
    """
    Read-only implementation of ProvenanceQueryService.

    - Never mutates provenance records.
    - Returns an empty tuple when no records exist for entity_id.
    - Returns None when no record exists for fact_id.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def list_provenance(
        self,
        entity_id: EntityId,
    ) -> tuple[Provenance, ...]:
        """Return all Provenance records for the given entity."""
        cursor = self._db.connection.execute(
            _SELECT_PROVENANCE + """
            WHERE entity_id = ?
            ORDER BY created_at ASC
            """,
            (str(entity_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_provenance(row) for row in rows)

    def get_provenance_by_fact(
        self,
        fact_id: FactId,
    ) -> Provenance | None:
        """Return the Provenance record for a specific fact, or None."""
        cursor = self._db.connection.execute(
            _SELECT_PROVENANCE + """
            WHERE fact_id = ?
            """,
            (str(fact_id),),
        )
        row: sqlite3.Row | None = cursor.fetchone()
        return _row_to_provenance(row) if row is not None else None
