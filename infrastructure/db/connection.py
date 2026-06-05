from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_lock = threading.Lock()
_instance: DatabaseConnection | None = None

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_PRAGMAS = """\
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
"""


class DatabaseConnection:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._local = threading.local()

    @property
    def connection(self) -> sqlite3.Connection:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self._db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.executescript(_PRAGMAS)
            self._local.conn = conn
        return conn

    def bootstrap(self) -> None:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self.connection.executescript(_PRAGMAS + schema_sql)

    def close(self) -> None:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


def init_db(db_path: str | Path) -> DatabaseConnection:
    global _instance
    with _lock:
        if _instance is None:
            _instance = DatabaseConnection(db_path)
            _instance.bootstrap()
    return _instance


def get_db() -> DatabaseConnection:
    if _instance is None:
        raise RuntimeError("Database not initialised. Call init_db(db_path) first.")
    return _instance
