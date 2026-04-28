import sqlite3
from pathlib import Path
from config import DB


class Database:

    def __init__(self):
        self.path = DB["path"]
        self.timeout = DB["timeout"]
        self.connection: sqlite3.Connection | None = None

    def connect(self):
        self.connection = sqlite3.connect(self.path, timeout=self.timeout)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        return self.connection

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def initialize(self):
        schema_path = Path(__file__).parent / "schema.sql"
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executescript(schema_path.read_text(encoding="utf-8"))
        conn.commit()
        self.disconnect()

    def execute(self, query: str, params: tuple = ()):
        if not self.connection:
            raise RuntimeError("No active connection. Use with Database() as db.")
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def fetchall(self, query: str, params: tuple = ()):
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def fetchone(self, query: str, params: tuple = ()):
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def commit(self):
        if self.connection:
            self.connection.commit()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        self.disconnect()
