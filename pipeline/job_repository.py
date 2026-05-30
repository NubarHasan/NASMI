from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from core.guards import require
from core.time import utcnow_iso
from pipeline.job import Job, JobStatus

_log = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id     TEXT PRIMARY KEY,
    job_type   TEXT    NOT NULL,
    priority   INTEGER NOT NULL,
    status     TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    blob       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs (job_type);
"""


@runtime_checkable
class JobRepository(Protocol):
    def save(self, job: Job) -> None: ...
    def load(self, job_id: str) -> Job | None: ...
    def exists(self, job_id: str) -> bool: ...
    def delete(self, job_id: str) -> None: ...
    def list_by_status(self, status: JobStatus) -> list[Job]: ...
    def list_all(self) -> list[Job]: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._store: dict[str, Job] = {}

    def save(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        with self._lock:
            self._store[job.job_id] = job

    def load(self, job_id: str) -> Job | None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        with self._lock:
            return self._store.get(job_id)

    def exists(self, job_id: str) -> bool:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        with self._lock:
            return job_id in self._store

    def delete(self, job_id: str) -> None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        with self._lock:
            self._store.pop(job_id, None)

    def list_by_status(self, status: JobStatus) -> list[Job]:
        require(isinstance(status, JobStatus), "status must be a JobStatus")
        with self._lock:
            return [j for j in self._store.values() if j.status == status]

    def list_all(self) -> list[Job]:
        with self._lock:
            return list(self._store.values())


class SQLiteJobRepository:
    def __init__(self, db_path: Path) -> None:
        require(isinstance(db_path, Path), "db_path must be a Path")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_DDL)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def save(self, job: Job) -> None:
        require(isinstance(job, Job), "job must be a Job")
        now = utcnow_iso()
        blob = json.dumps(job.to_dict(), ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO jobs
                    (job_id, job_type, priority, status, created_at, updated_at, blob)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status     = excluded.status,
                    priority   = excluded.priority,
                    updated_at = excluded.updated_at,
                    blob       = excluded.blob
                """,
                (
                    job.job_id,
                    str(job.job_type),
                    int(job.priority),
                    str(job.status),
                    job.created_at,
                    now,
                    blob,
                ),
            )
            self._conn.commit()

    def delete(self, job_id: str) -> None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        with self._lock:
            self._conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            self._conn.commit()

    def load(self, job_id: str) -> Job | None:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        with self._lock:
            row = self._conn.execute(
                "SELECT blob FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return _deserialise(row["blob"])

    def exists(self, job_id: str) -> bool:
        require(isinstance(job_id, str) and bool(job_id), "job_id must be non-empty")
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return row is not None

    def list_by_status(self, status: JobStatus) -> list[Job]:
        require(isinstance(status, JobStatus), "status must be a JobStatus")
        with self._lock:
            rows = self._conn.execute(
                "SELECT blob FROM jobs WHERE status = ?", (str(status),)
            ).fetchall()
        return [_deserialise(r["blob"]) for r in rows]

    def list_all(self) -> list[Job]:
        with self._lock:
            rows = self._conn.execute("SELECT blob FROM jobs").fetchall()
        return [_deserialise(r["blob"]) for r in rows]


def _deserialise(blob: str) -> Job:
    data: dict[str, Any] = json.loads(blob)
    return Job.from_dict(data)
