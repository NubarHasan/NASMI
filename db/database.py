import sqlite3
from config import DB


class Database:

    def __init__(self):
        self.path = DB["path"]
        self.timeout = DB["timeout"]
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.path, timeout=self.timeout)
        self.connection.row_factory = sqlite3.Row
        return self.connection

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                file_type   TEXT NOT NULL,
                file_size   REAL,
                uploaded_at TEXT DEFAULT (datetime('now')),
                status      TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS extractions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                method      TEXT NOT NULL,
                raw_text    TEXT,
                confidence  REAL,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS results (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                extraction_id INTEGER NOT NULL,
                entity_type   TEXT,
                entity_value  TEXT,
                model_used    TEXT,
                created_at    TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (extraction_id) REFERENCES extractions(id)
            );
        """
        )

        conn.commit()
        self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
