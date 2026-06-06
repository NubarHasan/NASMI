from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from core.guards import require
from core.identifiers import is_valid_form_submission_id, is_valid_form_template_id
from core.types import FormFieldId, FormSubmissionId, FormTemplateId
from forms.form_submission import FormSubmission, SubmissionEntry
from forms.form_type import SubmissionStatus
from infrastructure.db.sqlite_helpers import deserialize_json, serialize_json

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection


_INSERT_OR_REPLACE = """
INSERT INTO form_submissions (
    submission_id, template_id, version,
    status, entries, submitted_at, metadata
) VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(submission_id) DO UPDATE SET
    template_id  = excluded.template_id,
    version      = excluded.version,
    status       = excluded.status,
    entries      = excluded.entries,
    submitted_at = excluded.submitted_at,
    metadata     = excluded.metadata
"""

_SELECT_BY_ID = """
SELECT submission_id, template_id, version,
       status, entries, submitted_at, metadata
FROM form_submissions
WHERE submission_id = ?
"""

_SELECT_BY_TEMPLATE_ID = """
SELECT submission_id, template_id, version,
       status, entries, submitted_at, metadata
FROM form_submissions
WHERE template_id = ?
"""

_SELECT_BY_STATUS = """
SELECT submission_id, template_id, version,
       status, entries, submitted_at, metadata
FROM form_submissions
WHERE status = ?
"""

_EXISTS = "SELECT 1 FROM form_submissions WHERE submission_id = ? LIMIT 1"


def _entry_to_dict(e: SubmissionEntry) -> dict[str, Any]:
    return {"field_id": e.field_id, "value": e.value}


def _entry_from_dict(d: dict[str, Any]) -> SubmissionEntry:
    return SubmissionEntry(
        field_id=FormFieldId(d["field_id"]),
        value=d["value"],
    )


def _submission_to_row(s: FormSubmission) -> tuple[Any, ...]:
    return (
        s.submission_id,
        s.template_id,
        s.version,
        s.status.value,
        json.dumps([_entry_to_dict(e) for e in s.entries]),
        s.submitted_at.isoformat() if s.submitted_at else None,
        serialize_json(dict(s.metadata)),
    )


def _row_to_submission(row: sqlite3.Row) -> FormSubmission:
    d = dict(row)
    entries = tuple(_entry_from_dict(e) for e in json.loads(d["entries"]))
    submitted_at: datetime | None = None
    if d["submitted_at"]:
        submitted_at = datetime.fromisoformat(d["submitted_at"]).replace(tzinfo=UTC)
    return FormSubmission(
        submission_id=FormSubmissionId(d["submission_id"]),
        template_id=FormTemplateId(d["template_id"]),
        version=d["version"],
        status=SubmissionStatus(d["status"]),
        entries=entries,
        submitted_at=submitted_at,
        metadata=deserialize_json(d["metadata"]),
    )


class SqliteFormSubmissionRepository:
    """
    Infrastructure Implementation.

    Implements FormSubmissionRepository Protocol using SQLite.
    Persists FormSubmission objects to the form_submissions table.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, submission: FormSubmission) -> None:
        require(
            isinstance(submission, FormSubmission),
            "submission must be a FormSubmission",
        )
        self._conn.execute(_INSERT_OR_REPLACE, _submission_to_row(submission))
        self._conn.commit()

    def get_by_id(self, submission_id: FormSubmissionId) -> FormSubmission | None:
        require(
            is_valid_form_submission_id(submission_id),
            "submission_id has invalid format",
        )
        row = self._conn.execute(_SELECT_BY_ID, (submission_id,)).fetchone()
        return _row_to_submission(row) if row else None

    def get_by_template_id(self, template_id: FormTemplateId) -> list[FormSubmission]:
        require(
            is_valid_form_template_id(template_id),
            "template_id has invalid format",
        )
        rows = self._conn.execute(_SELECT_BY_TEMPLATE_ID, (template_id,)).fetchall()
        return [_row_to_submission(r) for r in rows]

    def get_by_status(self, status: SubmissionStatus) -> list[FormSubmission]:
        require(
            isinstance(status, SubmissionStatus),
            "status must be a SubmissionStatus",
        )
        rows = self._conn.execute(_SELECT_BY_STATUS, (status.value,)).fetchall()
        return [_row_to_submission(r) for r in rows]

    def exists(self, submission_id: FormSubmissionId) -> bool:
        require(
            is_valid_form_submission_id(submission_id),
            "submission_id has invalid format",
        )
        row = self._conn.execute(_EXISTS, (submission_id,)).fetchone()
        return row is not None
