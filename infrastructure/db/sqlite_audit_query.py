from __future__ import annotations

import json
import sqlite3

from audit.audit_chain import AuditChain
from audit.audit_entry import AuditEntry, AuditEventType
from core.types import EntityId, JobId
from infrastructure.db.connection import DatabaseConnection

_SELECT_AUDIT = """
    SELECT
        audit_id,
        event_type,
        job_id,
        subject_id,
        occurred_at,
        actor,
        message,
        metadata,
        previous_hash,
        entry_hash
    FROM audit_entries
"""


def _row_to_entry(row: sqlite3.Row) -> AuditEntry:
    return AuditEntry.from_dict(
        {
            "audit_id": row["audit_id"],
            "event_type": row["event_type"],
            "job_id": row["job_id"],
            "subject_id": row["subject_id"],
            "occurred_at": row["occurred_at"],
            "actor": row["actor"],
            "message": row["message"],
            "metadata": json.loads(row["metadata"] or "{}"),
            "previous_hash": row["previous_hash"],
            "entry_hash": row["entry_hash"],
        }
    )


class SqliteAuditQuery:
    """
    Read-only implementation of AuditQuery.

    - Never mutates audit records.
    - get_chain() returns AuditChain ordered by sequence_number ASC.
    - All list_* methods return tuple[AuditEntry, ...].
    - get_latest_by_entity() returns AuditEntry | None.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def get_chain(
        self,
        subject_id: EntityId,
    ) -> AuditChain:
        """Return the full AuditChain for the given subject, ordered by sequence_number."""
        cursor = self._db.connection.execute(
            _SELECT_AUDIT + """
            WHERE subject_id = ?
            ORDER BY sequence_number ASC
            """,
            (str(subject_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return AuditChain.from_entries(_row_to_entry(row) for row in rows)

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[AuditEntry, ...]:
        """Return all audit entries for the given entity, ordered by sequence_number."""
        cursor = self._db.connection.execute(
            _SELECT_AUDIT + """
            WHERE subject_id = ?
            ORDER BY sequence_number ASC
            """,
            (str(entity_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_entry(row) for row in rows)

    def list_by_job(
        self,
        job_id: JobId,
    ) -> tuple[AuditEntry, ...]:
        """Return all audit entries for the given job, ordered by sequence_number."""
        cursor = self._db.connection.execute(
            _SELECT_AUDIT + """
            WHERE job_id = ?
            ORDER BY sequence_number ASC
            """,
            (str(job_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_entry(row) for row in rows)

    def list_by_event_type(
        self,
        event_type: AuditEventType,
    ) -> tuple[AuditEntry, ...]:
        """Return all audit entries of the given event type, ordered by sequence_number."""
        cursor = self._db.connection.execute(
            _SELECT_AUDIT + """
            WHERE event_type = ?
            ORDER BY sequence_number ASC
            """,
            (event_type.value,),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_entry(row) for row in rows)

    def get_latest_by_entity(
        self,
        entity_id: EntityId,
    ) -> AuditEntry | None:
        """Return the most recent audit entry for the given entity, or None."""
        cursor = self._db.connection.execute(
            _SELECT_AUDIT + """
            WHERE subject_id = ?
            ORDER BY sequence_number DESC
            LIMIT 1
            """,
            (str(entity_id),),
        )
        row: sqlite3.Row | None = cursor.fetchone()
        return _row_to_entry(row) if row is not None else None
