from __future__ import annotations

import sqlite3
from typing import Any

from application.ports.document_repository import DocumentRepository
from archive.document import Document, DocumentStatus
from core.types import DocumentId, EntityId
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.sqlite_helpers import (
    deserialize_json,
    row_to_dict,
    serialize_json,
)


class SqliteDocumentRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> Document:
        d: dict[str, Any] = row_to_dict(row)
        return Document(
            document_id=DocumentId(d["document_id"]),
            entity_id=d["entity_id"],
            doc_type=d["doc_type"],
            file_hash=d["file_hash"],
            file_path=d["file_path"],
            language=d["language"],
            status=DocumentStatus(d["status"]),
            created_at=d["created_at"],
            issued_at=d.get("issued_at"),
            expires_at=d.get("expires_at"),
            metadata=deserialize_json(d.get("metadata")) or {},
        )

    def save(self, document: Document) -> None:
        sql = """
            INSERT INTO documents (
                document_id,
                entity_id,
                doc_type,
                file_hash,
                file_path,
                language,
                status,
                created_at,
                issued_at,
                expires_at,
                metadata
            ) VALUES (
                :document_id,
                :entity_id,
                :doc_type,
                :file_hash,
                :file_path,
                :language,
                :status,
                :created_at,
                :issued_at,
                :expires_at,
                :metadata
            )
            ON CONFLICT(document_id) DO UPDATE SET
                entity_id  = excluded.entity_id,
                doc_type   = excluded.doc_type,
                file_hash  = excluded.file_hash,
                file_path  = excluded.file_path,
                language   = excluded.language,
                status     = excluded.status,
                issued_at  = excluded.issued_at,
                expires_at = excluded.expires_at,
                metadata   = excluded.metadata
            ON CONFLICT(file_hash) DO UPDATE SET
                document_id = excluded.document_id,
                entity_id   = excluded.entity_id,
                doc_type    = excluded.doc_type,
                file_path   = excluded.file_path,
                language    = excluded.language,
                status      = excluded.status,
                issued_at   = excluded.issued_at,
                expires_at  = excluded.expires_at,
                metadata    = excluded.metadata
        """
        params: dict[str, Any] = {
            "document_id": document.document_id,
            "entity_id": document.entity_id,
            "doc_type": document.doc_type,
            "file_hash": document.file_hash,
            "file_path": document.file_path,
            "language": document.language,
            "status": str(document.status),
            "created_at": document.created_at,
            "issued_at": document.issued_at,
            "expires_at": document.expires_at,
            "metadata": serialize_json(document.metadata),
        }
        self._conn.execute(sql, params)

    def get(self, document_id: DocumentId) -> Document | None:
        sql = "SELECT * FROM documents WHERE document_id = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (document_id,)).fetchone()
        return self._row_to_document(row) if row else None

    def get_by_hash(self, file_hash: str) -> Document | None:
        sql = "SELECT * FROM documents WHERE file_hash = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (file_hash,)).fetchone()
        return self._row_to_document(row) if row else None

    def exists(self, document_id: DocumentId) -> bool:
        sql = "SELECT 1 FROM documents WHERE document_id = ? LIMIT 1"
        return self._conn.execute(sql, (document_id,)).fetchone() is not None

    def exists_by_hash(self, file_hash: str) -> bool:
        sql = "SELECT 1 FROM documents WHERE file_hash = ? LIMIT 1"
        return self._conn.execute(sql, (file_hash,)).fetchone() is not None

    def list_by_entity(self, entity_id: EntityId) -> tuple[Document, ...]:
        sql = "SELECT * FROM documents WHERE entity_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (entity_id,)).fetchall()
        return tuple(self._row_to_document(r) for r in rows)

    def list_by_status(self, status: DocumentStatus) -> tuple[Document, ...]:
        sql = "SELECT * FROM documents WHERE status = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (str(status),)).fetchall()
        return tuple(self._row_to_document(r) for r in rows)

    def list_by_entity_and_status(
        self,
        entity_id: EntityId,
        status: DocumentStatus,
    ) -> tuple[Document, ...]:
        sql = """
            SELECT * FROM documents
            WHERE entity_id = ? AND status = ?
            ORDER BY created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(
            sql, (entity_id, str(status))
        ).fetchall()
        return tuple(self._row_to_document(r) for r in rows)


def _assert_protocol() -> None:
    _: DocumentRepository = SqliteDocumentRepository.__new__(SqliteDocumentRepository)


_assert_protocol()
