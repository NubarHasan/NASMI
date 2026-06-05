from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def deserialize_json(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


def deserialize_json_list(value: str | None) -> list[Any]:
    if value is None:
        return []
    result = json.loads(value)
    return result if isinstance(result, list) else []


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def assert_affected(cursor: sqlite3.Cursor, expected: int = 1) -> None:
    if cursor.rowcount != expected:
        raise RuntimeError(
            f"Expected {expected} affected row(s), got {cursor.rowcount}."
        )
