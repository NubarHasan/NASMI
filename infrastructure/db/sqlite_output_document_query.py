from __future__ import annotations

import sqlite3
from pathlib import Path

from core.time import parse_timestamp
from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId
from output.output_type import OutputType

_SELECT_OUTPUT_DOCUMENT = """
    SELECT
        output_document_id,
        subject_id,
        output_type,
        output_format,
        generated_at,
        file_path
    FROM output_documents
"""


def _row_to_output_document(row: sqlite3.Row) -> OutputDocument:
    return OutputDocument(
        output_document_id=OutputDocumentId(row["output_document_id"]),
        subject_id=EntityId(row["subject_id"]),
        output_type=OutputType(row["output_type"]),
        output_format=OutputFormat(row["output_format"]),
        generated_at=parse_timestamp(row["generated_at"]),
        file_path=Path(row["file_path"]),
    )


class SqliteOutputDocumentQuery:
    """
    Read-only implementation of OutputDocumentQueryService.

    - Never mutates output_document records.
    - get_by_id() returns OutputDocument | None.
    - list_by_subject() returns tuple[OutputDocument, ...].
    - content_hash is intentionally excluded: not part of OutputDocument domain.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def get_by_id(
        self,
        output_document_id: OutputDocumentId,
    ) -> OutputDocument | None:
        """Return the OutputDocument with the given ID, or None."""
        cursor = self._db.connection.execute(
            _SELECT_OUTPUT_DOCUMENT + """
            WHERE output_document_id = ?
            """,
            (str(output_document_id),),
        )
        row: sqlite3.Row | None = cursor.fetchone()
        return _row_to_output_document(row) if row is not None else None

    def list_by_subject(
        self,
        subject_id: EntityId,
    ) -> tuple[OutputDocument, ...]:
        """Return all output documents for the given subject, ordered by generated_at."""
        cursor = self._db.connection.execute(
            _SELECT_OUTPUT_DOCUMENT + """
            WHERE subject_id = ?
            ORDER BY generated_at ASC
            """,
            (str(subject_id),),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()
        return tuple(_row_to_output_document(row) for row in rows)
