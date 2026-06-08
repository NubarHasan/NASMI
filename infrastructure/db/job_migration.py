from __future__ import annotations

import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_table_sql(conn: sqlite3.Connection, table_name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return str(row[0]) if row and row[0] else ""


def migrate_jobs(conn: sqlite3.Connection) -> None:
    sql = get_table_sql(conn, "jobs")

    if not sql:
        conn.execute("""
            CREATE TABLE jobs (
                job_id     TEXT PRIMARY KEY,
                job_type   TEXT    NOT NULL,
                priority   INTEGER NOT NULL,
                status     TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL,
                blob       TEXT    NOT NULL
            )
            """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type)")
        return

    if "blob" in sql and "payload_hash" not in sql:
        return

    conn.execute("DROP TABLE IF EXISTS jobs_old")
    conn.execute("ALTER TABLE jobs RENAME TO jobs_old")

    conn.execute("""
        CREATE TABLE jobs (
            job_id     TEXT PRIMARY KEY,
            job_type   TEXT    NOT NULL,
            priority   INTEGER NOT NULL,
            status     TEXT    NOT NULL,
            created_at TEXT    NOT NULL,
            updated_at TEXT    NOT NULL,
            blob       TEXT    NOT NULL
        )
        """)

    rows = conn.execute("""
        SELECT job_id, job_type, priority, status, created_at, updated_at, payload_hash, context
        FROM jobs_old
        """).fetchall()

    for row in rows:
        job_id = str(row[0])
        job_type = str(row[1])
        priority_raw = row[2]
        status = str(row[3])
        created_at = str(row[4])
        updated_at = str(row[5])
        payload_hash = str(row[6])
        context = str(row[7] or "{}")

        try:
            priority = int(priority_raw)
        except Exception:
            priority = 20

        blob = {
            "job_id": job_id,
            "job_type": job_type,
            "priority": priority,
            "status": status,
            "created_at": created_at,
            "payload_hash": payload_hash,
            "payload": {},
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "retry_count": 0,
            "max_retries": 3,
            "context": {},
        }

        conn.execute(
            """
            INSERT INTO jobs (
                job_id,
                job_type,
                priority,
                status,
                created_at,
                updated_at,
                blob
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job_type,
                priority,
                status,
                created_at,
                updated_at,
                __import__("json").dumps(blob, ensure_ascii=False),
            ),
        )

    conn.execute("DROP TABLE jobs_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type)")


def create_job_queue(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_queue (
            job_id       TEXT PRIMARY KEY,
            priority     INTEGER NOT NULL,
            status       TEXT    NOT NULL,
            created_at   TEXT    NOT NULL,
            updated_at   TEXT    NOT NULL,
            available_at TEXT    NOT NULL
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_queue_available_at ON job_queue(available_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_queue_priority ON job_queue(priority)"
    )


def create_entity_relationships(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_relationships (
            relationship_id TEXT PRIMARY KEY,
            source_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            target_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            relation_type TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0 CHECK (
                confidence >= 0.0
                AND confidence <= 1.0
            ),
            created_at TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            UNIQUE(source_entity_id, target_entity_id, relation_type)
        )
        """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_relationships_relation_type ON entity_relationships(relation_type)"
    )


def run_phase4_schema_migration(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA journal_mode=WAL")

    migrate_jobs(conn)
    create_job_queue(conn)
    create_entity_relationships(conn)

    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()


if __name__ == "__main__":
    run_phase4_schema_migration(Path("data/nasmi.db"))
