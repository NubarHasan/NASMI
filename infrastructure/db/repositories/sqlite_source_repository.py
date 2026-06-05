from __future__ import annotations

import sqlite3
from typing import Any

from application.ports.source_repository import SourceRepository
from archive.source import Source, SourceType
from core.types import DocumentId, EntityId, SourceId
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.sqlite_helpers import (
    deserialize_json,
    row_to_dict,
    serialize_json,
)


class SqliteSourceRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    @staticmethod
    def _row_to_source(row: sqlite3.Row) -> Source:
        d: dict[str, Any] = row_to_dict(row)
        return Source(
            source_id=SourceId(d["source_id"]),
            entity_id=EntityId(d["entity_id"]),
            source_type=SourceType(d["source_type"]),
            created_at=d["created_at"],
            document_id=DocumentId(d["document_id"]) if d.get("document_id") else None,
            metadata=deserialize_json(d.get("metadata")) or {},
        )

    def save(self, source: Source) -> None:
        sql = """
            INSERT INTO sources (
                source_id,
                entity_id,
                source_type,
                created_at,
                document_id,
                metadata
            ) VALUES (
                :source_id,
                :entity_id,
                :source_type,
                :created_at,
                :document_id,
                :metadata
            )
            ON CONFLICT(source_id) DO UPDATE SET
                entity_id   = excluded.entity_id,
                source_type = excluded.source_type,
                created_at  = excluded.created_at,
                document_id = excluded.document_id,
                metadata    = excluded.metadata
        """
        params: dict[str, Any] = {
            "source_id": source.source_id,
            "entity_id": source.entity_id,
            "source_type": str(source.source_type),
            "created_at": source.created_at,
            "document_id": source.document_id,
            "metadata": serialize_json(source.metadata),
        }
        self._conn.execute(sql, params)

    def get(self, source_id: SourceId) -> Source | None:
        sql = "SELECT * FROM sources WHERE source_id = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (source_id,)).fetchone()
        return self._row_to_source(row) if row else None

    def exists(self, source_id: SourceId) -> bool:
        sql = "SELECT 1 FROM sources WHERE source_id = ? LIMIT 1"
        return self._conn.execute(sql, (source_id,)).fetchone() is not None

    def list_by_entity(self, entity_id: EntityId) -> tuple[Source, ...]:
        sql = "SELECT * FROM sources WHERE entity_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (entity_id,)).fetchall()
        return tuple(self._row_to_source(r) for r in rows)

    def list_by_document(self, document_id: DocumentId) -> tuple[Source, ...]:
        sql = "SELECT * FROM sources WHERE document_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (document_id,)).fetchall()
        return tuple(self._row_to_source(r) for r in rows)


def _assert_protocol() -> None:
    _: SourceRepository = SqliteSourceRepository.__new__(SqliteSourceRepository)


_assert_protocol()
