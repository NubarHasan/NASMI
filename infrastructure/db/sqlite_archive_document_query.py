from __future__ import annotations

import sqlite3

from archive.document import Document
from core.types import DocumentId, EntityId
from infrastructure.db.connection import DatabaseConnection

_SELECT_DOCUMENT = """
    SELECT
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
    FROM documents
"""


def _row_to_document(row: sqlite3.Row) -> Document:
    import json

    return Document.from_dict(
        {
            "document_id": row["document_id"],
            "entity_id": row["entity_id"],
            "doc_type": row["doc_type"],
            "file_hash": row["file_hash"],
            "file_path": row["file_path"],
            "language": row["language"],
            "status": row["status"],
            "created_at": row["created_at"],
            "issued_at": row["issued_at"],
            "expires_at": row["expires_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
    )


class SqliteArchiveDocumentQuery:
    """
    Read-only implementation of ArchiveDocumentQueryService.

    - Never mutates document records.
    - get_by_id() returns Document | None.
    - list_by_subject() returns tuple[Document, ...].
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def get_by_id(
        self,
        document_id: DocumentId,
    ) -> Document | None:
        """Return the Document with the given ID, or None."""
        cursor = self._db.connection.execute(
            _SELECT_DOCUMENT + """
            WHERE document_id = ?
            """,
            (str(document_id),),
        )
        row: sqlite3.Row | None = cursor.fetchone()
        return _row_to_document(row) if row is not None else None

    def list_by_subject(
        self,
        subject_id: EntityId,
    ) -> tuple[Document, ...]:
        """Return all documents for the given subject, ordered by created_at."""
        cursor = self._db.connection.execute(
            _SELECT_DOCUMENT + """
            WHERE entity_id = ?
            ORDER BY created_at ASC
            """,
            (str(subject_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_document(row) for row in rows)
