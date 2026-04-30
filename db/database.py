from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from config import DB


class Database:

    def __init__(self) -> None:
        self.path    = DB['path']
        self.timeout = DB['timeout']
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        self.connection = sqlite3.connect(self.path, timeout=self.timeout)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA foreign_keys=ON')
        return self.connection

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def initialize(self) -> None:
        schema_path = Path(__file__).parent / 'schema.sql'
        conn = self.connect()
        conn.cursor().executescript(schema_path.read_text(encoding='utf-8'))
        conn.commit()
        self.disconnect()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        return [dict(row) for row in self.execute(query, params).fetchall()]

    def fetchone(self, query: str, params: tuple = ()) -> dict | None:
        row = self.execute(query, params).fetchone()
        return dict(row) if row else None

    def commit(self) -> None:
        if self.connection:
            self.connection.commit()

    def rollback(self) -> None:
        if self.connection:
            self.connection.rollback()

    @contextmanager
    def transaction(self):
        """
        Atomic block — commits on success, rolls back on any exception.

        Usage:
            with db.transaction():
                model_a.insert(db, ...)
                model_b.upsert(db, ...)
        """
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

    def __enter__(self) -> 'Database':
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.disconnect()