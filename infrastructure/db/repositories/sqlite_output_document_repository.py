from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from application.ports.profile_snapshot_repository import OutputDocumentRepository
from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId
from output.output_type import OutputType


def _compute_content_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _row_to_document(row: sqlite3.Row) -> OutputDocument:
    return OutputDocument(
        output_document_id=OutputDocumentId(row["output_document_id"]),
        subject_id=EntityId(row["subject_id"]),
        output_type=OutputType(row["output_type"]),
        output_format=OutputFormat(row["output_format"]),
        generated_at=datetime.fromisoformat(row["generated_at"]).replace(tzinfo=UTC),
        file_path=Path(row["file_path"]),
    )


class SqliteOutputDocumentRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, document: OutputDocument) -> None:
        content_hash = _compute_content_hash(document.file_path)
        self._conn.execute(
            """
            INSERT INTO output_documents (
                output_document_id,
                subject_id,
                output_type,
                output_format,
                generated_at,
                file_path,
                content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (output_document_id) DO UPDATE SET
                output_type   = excluded.output_type,
                output_format = excluded.output_format,
                generated_at  = excluded.generated_at,
                file_path     = excluded.file_path,
                content_hash  = excluded.content_hash
            """,
            (
                str(document.output_document_id),
                str(document.subject_id),
                document.output_type.value,
                document.output_format.value,
                document.generated_at.isoformat(),
                str(document.file_path),
                content_hash,
            ),
        )

    def get(
        self,
        output_document_id: OutputDocumentId,
    ) -> OutputDocument | None:
        row = self._conn.execute(
            """
            SELECT
                output_document_id,
                subject_id,
                output_type,
                output_format,
                generated_at,
                file_path
            FROM output_documents
            WHERE output_document_id = ?
            """,
            (str(output_document_id),),
        ).fetchone()
        if row is None:
            return None
        return _row_to_document(row)

    def exists(
        self,
        output_document_id: OutputDocumentId,
    ) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM output_documents WHERE output_document_id = ?",
            (str(output_document_id),),
        ).fetchone()
        return row is not None

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[OutputDocument, ...]:
        rows = self._conn.execute(
            """
            SELECT
                output_document_id,
                subject_id,
                output_type,
                output_format,
                generated_at,
                file_path
            FROM output_documents
            WHERE subject_id = ?
            ORDER BY generated_at DESC
            """,
            (str(entity_id),),
        ).fetchall()
        return tuple(_row_to_document(row) for row in rows)

    def list_by_entity_and_type(
        self,
        entity_id: EntityId,
        output_type: OutputType,
    ) -> tuple[OutputDocument, ...]:
        rows = self._conn.execute(
            """
            SELECT
                output_document_id,
                subject_id,
                output_type,
                output_format,
                generated_at,
                file_path
            FROM output_documents
            WHERE subject_id = ?
              AND output_type = ?
            ORDER BY generated_at DESC
            """,
            (str(entity_id), output_type.value),
        ).fetchall()
        return tuple(_row_to_document(row) for row in rows)

    def get_latest_by_entity_and_type(
        self,
        entity_id: EntityId,
        output_type: OutputType,
    ) -> OutputDocument | None:
        row = self._conn.execute(
            """
            SELECT
                output_document_id,
                subject_id,
                output_type,
                output_format,
                generated_at,
                file_path
            FROM output_documents
            WHERE subject_id = ?
              AND output_type = ?
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            (str(entity_id), output_type.value),
        ).fetchone()
        if row is None:
            return None
        return _row_to_document(row)


def _assert_protocol() -> None:
    _: OutputDocumentRepository = SqliteOutputDocumentRepository.__new__(
        SqliteOutputDocumentRepository
    )


_assert_protocol()
