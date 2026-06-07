from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection


@dataclass(frozen=True)
class NoiseItem:
    noise_id: str
    entity_id: str | None
    document_id: str | None
    source_id: str | None
    stage: str
    raw_text: str
    reason: str
    confidence: float
    status: str
    created_at: str
    reviewed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


_INSERT = """
INSERT INTO noise_items (
    noise_id,
    entity_id,
    document_id,
    source_id,
    stage,
    raw_text,
    reason,
    confidence,
    status,
    created_at,
    reviewed_at,
    metadata
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_SELECT_BY_ID = """
SELECT
    noise_id,
    entity_id,
    document_id,
    source_id,
    stage,
    raw_text,
    reason,
    confidence,
    status,
    created_at,
    reviewed_at,
    metadata
FROM noise_items
WHERE noise_id = ?
"""

_LIST_OPEN = """
SELECT
    noise_id,
    entity_id,
    document_id,
    source_id,
    stage,
    raw_text,
    reason,
    confidence,
    status,
    created_at,
    reviewed_at,
    metadata
FROM noise_items
WHERE status = 'open'
ORDER BY created_at DESC
LIMIT ?
"""

_LIST_ALL = """
SELECT
    noise_id,
    entity_id,
    document_id,
    source_id,
    stage,
    raw_text,
    reason,
    confidence,
    status,
    created_at,
    reviewed_at,
    metadata
FROM noise_items
ORDER BY created_at DESC
LIMIT ?
"""

_LIST_BY_ENTITY = """
SELECT
    noise_id,
    entity_id,
    document_id,
    source_id,
    stage,
    raw_text,
    reason,
    confidence,
    status,
    created_at,
    reviewed_at,
    metadata
FROM noise_items
WHERE entity_id = ?
ORDER BY created_at DESC
LIMIT ?
"""

_COUNT_OPEN = """
SELECT COUNT(*) AS count
FROM noise_items
WHERE status = 'open'
"""

_UPDATE_STATUS = """
UPDATE noise_items
SET status = ?,
    reviewed_at = ?
WHERE noise_id = ?
"""

_UPDATE_TEXT = """
UPDATE noise_items
SET raw_text = ?,
    reason = ?,
    confidence = ?,
    metadata = ?
WHERE noise_id = ?
"""

_DELETE = """
DELETE FROM noise_items
WHERE noise_id = ?
"""


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_noise_item(row: sqlite3.Row) -> NoiseItem:
    return NoiseItem(
        noise_id=str(row["noise_id"]),
        entity_id=row["entity_id"],
        document_id=row["document_id"],
        source_id=row["source_id"],
        stage=str(row["stage"]),
        raw_text=str(row["raw_text"]),
        reason=str(row["reason"]),
        confidence=float(row["confidence"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        reviewed_at=row["reviewed_at"],
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
    )


class SqliteNoiseRepository:
    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def create(
        self,
        raw_text: str,
        reason: str,
        stage: str,
        entity_id: str | None = None,
        document_id: str | None = None,
        source_id: str | None = None,
        confidence: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> NoiseItem:
        item = NoiseItem(
            noise_id=f"noise_{uuid.uuid4().hex}",
            entity_id=entity_id,
            document_id=document_id,
            source_id=source_id,
            stage=stage,
            raw_text=raw_text,
            reason=reason,
            confidence=max(0.0, min(1.0, float(confidence))),
            status="open",
            created_at=_utcnow_iso(),
            reviewed_at=None,
            metadata=metadata or {},
        )

        self._conn.execute(
            _INSERT,
            (
                item.noise_id,
                item.entity_id,
                item.document_id,
                item.source_id,
                item.stage,
                item.raw_text,
                item.reason,
                item.confidence,
                item.status,
                item.created_at,
                item.reviewed_at,
                json.dumps(item.metadata, ensure_ascii=False),
            ),
        )
        self._conn.commit()
        return item

    def get(self, noise_id: str) -> NoiseItem | None:
        row = self._conn.execute(_SELECT_BY_ID, (noise_id,)).fetchone()
        return _row_to_noise_item(row) if row else None

    def list_open(self, limit: int = 20) -> tuple[NoiseItem, ...]:
        rows = self._conn.execute(_LIST_OPEN, (limit,)).fetchall()
        return tuple(_row_to_noise_item(row) for row in rows)

    def list_all(self, limit: int = 50) -> tuple[NoiseItem, ...]:
        rows = self._conn.execute(_LIST_ALL, (limit,)).fetchall()
        return tuple(_row_to_noise_item(row) for row in rows)

    def list_by_entity(self, entity_id: str, limit: int = 20) -> tuple[NoiseItem, ...]:
        rows = self._conn.execute(_LIST_BY_ENTITY, (entity_id, limit)).fetchall()
        return tuple(_row_to_noise_item(row) for row in rows)

    def count_open(self) -> int:
        row = self._conn.execute(_COUNT_OPEN).fetchone()
        return int(row["count"]) if row else 0

    def update_status(self, noise_id: str, status: str) -> None:
        if status not in {"open", "reviewed", "ignored", "promoted"}:
            raise ValueError(f"Invalid noise status: {status}")

        reviewed_at = None if status == "open" else _utcnow_iso()
        self._conn.execute(_UPDATE_STATUS, (status, reviewed_at, noise_id))
        self._conn.commit()

    def update_text(
        self,
        noise_id: str,
        raw_text: str,
        reason: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            _UPDATE_TEXT,
            (
                raw_text,
                reason,
                max(0.0, min(1.0, float(confidence))),
                json.dumps(metadata or {}, ensure_ascii=False),
                noise_id,
            ),
        )
        self._conn.commit()

    def delete(self, noise_id: str) -> None:
        self._conn.execute(_DELETE, (noise_id,))
        self._conn.commit()
