from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from infrastructure.db.connection import get_db


@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db().connection
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


@contextmanager
def read_only() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db().connection
    yield conn
