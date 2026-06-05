from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import datetime

from application.ports.audit_recorder import AuditRecorder
from audit.audit_entry import AuditEntry, AuditEventType
from core.time import format_timestamp
from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection


class SqliteAuditRecorder:

    def __init__(self, db: DatabaseConnection, secret_key: bytes) -> None:
        self._db = db
        self._secret_key = secret_key

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def _latest_entry_hash(self) -> str | None:
        row = self._conn.execute("""
            SELECT entry_hash
            FROM audit_entries
            ORDER BY sequence_number DESC
            LIMIT 1
            """).fetchone()
        return row["entry_hash"] if row is not None else None

    def _next_sequence_number(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_seq FROM audit_entries"
        ).fetchone()
        return int(row["next_seq"])

    @staticmethod
    def _build_message(
        event_type: AuditEventType,
        success: bool,
        error: str | None,
    ) -> str:
        if success:
            return str(event_type)
        if error:
            return f"{event_type}: {error}"
        return f"{event_type}: failed"

    @staticmethod
    def _build_metadata(
        payload: Mapping[str, object],
        occurred_at: datetime,
        success: bool,
        error: str | None,
    ) -> dict[str, object]:
        meta: dict[str, object] = {
            "event_occurred_at": format_timestamp(occurred_at),
            **payload,
        }
        if not success:
            meta["success"] = False
        if error is not None:
            meta["error"] = error
        return meta

    def record(
        self,
        event_type: AuditEventType,
        subject_id: EntityId | None,
        payload: Mapping[str, object],
        occurred_at: datetime,
        success: bool = True,
        error: str | None = None,
    ) -> AuditEntry:
        previous_hash = self._latest_entry_hash()

        message = self._build_message(event_type, success, error)
        meta = self._build_metadata(payload, occurred_at, success, error)

        entry = AuditEntry.create(
            secret_key=self._secret_key,
            event_type=event_type,
            message=message,
            subject_id=subject_id,
            metadata=meta,
            previous_hash=previous_hash,
        )

        sequence_number = self._next_sequence_number()
        description = error if error is not None else ""

        data = entry.to_dict()

        self._conn.execute(
            """
            INSERT INTO audit_entries (
                audit_id,
                event_type,
                job_id,
                subject_id,
                occurred_at,
                actor,
                message,
                metadata,
                previous_hash,
                entry_hash,
                sequence_number,
                description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["audit_id"],
                data["event_type"],
                data["job_id"],
                data["subject_id"],
                data["occurred_at"],
                data["actor"],
                data["message"],
                json.dumps(data["metadata"], ensure_ascii=False),
                data["previous_hash"],
                data["entry_hash"],
                sequence_number,
                description,
            ),
        )

        return entry


def _assert_protocol() -> None:
    _: AuditRecorder = SqliteAuditRecorder.__new__(SqliteAuditRecorder)


_assert_protocol()
