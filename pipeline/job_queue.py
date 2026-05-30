from __future__ import annotations

import sqlite3
import threading
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from core.guards import require
from core.time import format_timestamp, parse_timestamp, utcnow_iso

_DDL = """
CREATE TABLE IF NOT EXISTS job_queue (
    job_id       TEXT PRIMARY KEY,
    priority     INTEGER NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    available_at TEXT NOT NULL,
    retry_count  INTEGER NOT NULL DEFAULT 0
)
"""


class QueueStatus(StrEnum):
    PENDING = "pending"
    RETRYING = "retrying"
    LEASED = "leased"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobQueue:
    def __init__(self, db_path: Path) -> None:
        require(isinstance(db_path, Path), "db_path must be a Path")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(_DDL)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def enqueue(
        self,
        job_id: str,
        priority: int,
        created_at: str,
    ) -> None:
        require(isinstance(job_id, str), "job_id must be a string")
        require(len(job_id) > 0, "job_id must be non-empty")
        require(isinstance(priority, int), "priority must be an int")
        require(isinstance(created_at, str), "created_at must be a string")
        require(len(created_at) > 0, "created_at must be non-empty")
        now = utcnow_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO job_queue
                    (job_id, priority, status, created_at, updated_at, available_at, retry_count)
                VALUES
                    (?, ?, ?, ?, ?, ?, 0)
                """,
                (job_id, priority, QueueStatus.PENDING, created_at, now, now),
            )
            self._conn.commit()

    def lease(self) -> str | None:
        now = utcnow_iso()
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id
                FROM   job_queue
                WHERE  status IN (?, ?)
                AND    available_at <= ?
                ORDER  BY priority DESC, created_at ASC
                LIMIT  1
                """,
                (QueueStatus.PENDING, QueueStatus.RETRYING, now),
            ).fetchone()
            if row is None:
                return None
            job_id: str = row["job_id"]
            self._conn.execute(
                """
                UPDATE job_queue
                SET    status     = ?,
                       updated_at = ?
                WHERE  job_id = ?
                """,
                (QueueStatus.LEASED, now, job_id),
            )
            self._conn.commit()
            return job_id

    def complete(self, job_id: str) -> None:
        require(isinstance(job_id, str), "job_id must be a string")
        require(len(job_id) > 0, "job_id must be non-empty")
        now = utcnow_iso()
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE job_queue
                SET    status     = ?,
                       updated_at = ?
                WHERE  job_id = ?
                AND    status = ?
                """,
                (QueueStatus.COMPLETED, now, job_id, QueueStatus.LEASED),
            )
            self._conn.commit()
            require(cursor.rowcount == 1, f"job not leased: {job_id!r}")

    def requeue(self, job_id: str, delay_seconds: int = 0) -> None:
        require(isinstance(job_id, str), "job_id must be a string")
        require(len(job_id) > 0, "job_id must be non-empty")
        require(isinstance(delay_seconds, int), "delay_seconds must be an int")
        require(delay_seconds >= 0, "delay_seconds must be non-negative")
        now = utcnow_iso()
        available_at = _offset_iso(now, delay_seconds)
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE job_queue
                SET    status       = ?,
                       updated_at   = ?,
                       available_at = ?,
                       retry_count  = retry_count + 1
                WHERE  job_id = ?
                AND    status = ?
                """,
                (QueueStatus.RETRYING, now, available_at, job_id, QueueStatus.LEASED),
            )
            self._conn.commit()
            require(cursor.rowcount == 1, f"job not leased: {job_id!r}")

    def fail(self, job_id: str) -> None:
        require(isinstance(job_id, str), "job_id must be a string")
        require(len(job_id) > 0, "job_id must be non-empty")
        now = utcnow_iso()
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE job_queue
                SET    status     = ?,
                       updated_at = ?
                WHERE  job_id = ?
                AND    status = ?
                """,
                (QueueStatus.FAILED, now, job_id, QueueStatus.LEASED),
            )
            self._conn.commit()
            require(cursor.rowcount == 1, f"job not leased: {job_id!r}")

    def cancel(self, job_id: str) -> bool:
        require(isinstance(job_id, str), "job_id must be a string")
        require(len(job_id) > 0, "job_id must be non-empty")
        now = utcnow_iso()
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE job_queue
                SET    status     = ?,
                       updated_at = ?
                WHERE  job_id = ?
                AND    status IN (?, ?)
                """,
                (
                    QueueStatus.CANCELLED,
                    now,
                    job_id,
                    QueueStatus.PENDING,
                    QueueStatus.RETRYING,
                ),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def recover_leased(self) -> list[str]:
        """
        Startup-only recovery.
        Resets all leased jobs back to pending.
        Must be called once before any worker starts.
        Safe only in single-process context.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT job_id FROM job_queue WHERE status = ?",
                (QueueStatus.LEASED,),
            ).fetchall()
            job_ids: list[str] = [str(row["job_id"]) for row in rows]
            if job_ids:
                now = utcnow_iso()
                self._conn.execute(
                    """
                    UPDATE job_queue
                    SET    status     = ?,
                           updated_at = ?
                    WHERE  status = ?
                    """,
                    (QueueStatus.PENDING, now, QueueStatus.LEASED),
                )
                self._conn.commit()
            return job_ids

    def peek(self) -> str | None:
        now = utcnow_iso()
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id
                FROM   job_queue
                WHERE  status IN (?, ?)
                AND    available_at <= ?
                ORDER  BY priority DESC, created_at ASC
                LIMIT  1
                """,
                (QueueStatus.PENDING, QueueStatus.RETRYING, now),
            ).fetchone()
            return str(row["job_id"]) if row else None

    def get_status(self, job_id: str) -> QueueStatus | None:
        require(isinstance(job_id, str), "job_id must be a string")
        require(len(job_id) > 0, "job_id must be non-empty")
        with self._lock:
            row = self._conn.execute(
                "SELECT status FROM job_queue WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            return QueueStatus(row["status"]) if row else None

    def size(self) -> int:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM   job_queue
                WHERE  status IN (?, ?, ?)
                """,
                (QueueStatus.PENDING, QueueStatus.RETRYING, QueueStatus.LEASED),
            ).fetchone()
            return int(row["n"])

    def is_empty(self) -> bool:
        return self.size() == 0

    def all_rows(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM job_queue ORDER BY priority DESC, created_at ASC"
            ).fetchall()
            return [dict(row) for row in rows]


def _offset_iso(iso: str, seconds: int) -> str:
    dt = parse_timestamp(iso)
    return format_timestamp(dt + timedelta(seconds=seconds))
