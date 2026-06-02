from __future__ import annotations

import sqlite3
import threading
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

from core.guards import require
from core.time import format_timestamp, utcnow_iso

_DDL = """
CREATE TABLE IF NOT EXISTS job_queue (
    job_id       TEXT PRIMARY KEY,
    priority     INTEGER NOT NULL,
    status       TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    available_at TEXT    NOT NULL
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
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(_DDL)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def enqueue(self, job_id: str, priority: int, created_at: str) -> None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        require(isinstance(priority, int), "priority must be an int")
        require(
            isinstance(created_at, str) and bool(created_at),
            "created_at must be non-empty",
        )
        now = utcnow_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO job_queue
                    (job_id, priority, status, created_at, updated_at, available_at)
                VALUES (?, ?, ?, ?, ?, ?)
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
                "UPDATE job_queue SET status=?, updated_at=? WHERE job_id=?",
                (QueueStatus.LEASED, now, job_id),
            )
            self._conn.commit()
            return job_id

    def complete(self, job_id: str) -> None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        now = utcnow_iso()
        with self._lock:
            self._conn.execute(
                "UPDATE job_queue SET status=?, updated_at=? WHERE job_id=? AND status=?",
                (QueueStatus.COMPLETED, now, job_id, QueueStatus.LEASED),
            )
            self._conn.commit()

    def fail(self, job_id: str) -> None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        now = utcnow_iso()
        with self._lock:
            self._conn.execute(
                "UPDATE job_queue SET status=?, updated_at=? WHERE job_id=?",
                (QueueStatus.FAILED, now, job_id),
            )
            self._conn.commit()

    def requeue(self, job_id: str, delay_seconds: int) -> None:
        """
        يُعيد الـ job إلى القائمة بعد delay_seconds.
        عداد المحاولات يبقى في Job._retry_count — لا يُخزن هنا.
        """
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        require(
            isinstance(delay_seconds, int) and delay_seconds >= 0,
            "delay_seconds must be non-negative int",
        )
        from core.time import utcnow

        available_at = format_timestamp(utcnow() + timedelta(seconds=delay_seconds))
        now = utcnow_iso()
        with self._lock:
            self._conn.execute(
                """
                UPDATE job_queue
                SET    status       = ?,
                       updated_at   = ?,
                       available_at = ?
                WHERE  job_id = ?
                """,
                (QueueStatus.RETRYING, now, available_at, job_id),
            )
            self._conn.commit()

    def cancel(self, job_id: str) -> None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        now = utcnow_iso()
        with self._lock:
            self._conn.execute(
                "UPDATE job_queue SET status=?, updated_at=? WHERE job_id=?",
                (QueueStatus.CANCELLED, now, job_id),
            )
            self._conn.commit()

    def depth(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM job_queue WHERE status IN (?, ?)",
                (QueueStatus.PENDING, QueueStatus.RETRYING),
            ).fetchone()
            return int(row[0]) if row else 0
