from __future__ import annotations

import json
import sqlite3
from typing import Any

from application.ports.audit_query import AuditQuery
from audit.audit_chain import AuditChain
from audit.audit_entry import AuditEntry, AuditEventType
from core.types import EntityId, JobId
from infrastructure.db.connection import DatabaseConnection


def _row_to_entry(row: sqlite3.Row) -> AuditEntry:
    data: dict[str, Any] = {
        "audit_id": row["audit_id"],
        "event_type": row["event_type"],
        "job_id": row["job_id"],
        "subject_id": row["subject_id"],
        "occurred_at": row["occurred_at"],
        "actor": row["actor"],
        "message": row["message"],
        "metadata": json.loads(row["metadata"]),
        "previous_hash": row["previous_hash"],
        "entry_hash": row["entry_hash"],
    }
    return AuditEntry.from_dict(data)


_SELECT = """
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


class SqliteAuditQuery:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def get_chain(self, subject_id: EntityId) -> AuditChain:
        rows = self._conn.execute(
            _SELECT + "WHERE subject_id = ? ORDER BY sequence_number ASC",
            (str(subject_id),),
        ).fetchall()
        return AuditChain.from_entries(_row_to_entry(row) for row in rows)

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[AuditEntry, ...]:
        rows = self._conn.execute(
            _SELECT + "WHERE subject_id = ? ORDER BY sequence_number ASC",
            (str(entity_id),),
        ).fetchall()
        return tuple(_row_to_entry(row) for row in rows)

    def list_by_job(
        self,
        job_id: JobId,
    ) -> tuple[AuditEntry, ...]:
        rows = self._conn.execute(
            _SELECT + "WHERE job_id = ? ORDER BY sequence_number ASC",
            (str(job_id),),
        ).fetchall()
        return tuple(_row_to_entry(row) for row in rows)

    def list_by_event_type(
        self,
        event_type: AuditEventType,
    ) -> tuple[AuditEntry, ...]:
        rows = self._conn.execute(
            _SELECT + "WHERE event_type = ? ORDER BY sequence_number ASC",
            (event_type.value,),
        ).fetchall()
        return tuple(_row_to_entry(row) for row in rows)

    def get_latest_by_entity(
        self,
        entity_id: EntityId,
    ) -> AuditEntry | None:
        row = self._conn.execute(
            _SELECT + "WHERE subject_id = ? ORDER BY sequence_number DESC LIMIT 1",
            (str(entity_id),),
        ).fetchone()
        if row is None:
            return None
        return _row_to_entry(row)


def _assert_protocol() -> None:
    _: AuditQuery = SqliteAuditQuery.__new__(SqliteAuditQuery)


_assert_protocol()
