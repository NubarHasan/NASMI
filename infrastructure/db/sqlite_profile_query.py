from __future__ import annotations

import json
import sqlite3

from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from knowledge.profile import Profile

_SELECT_PROFILE = """
    SELECT
        profile_id,
        entity_id,
        entity_type,
        display_name,
        fields,
        completeness,
        computed_at,
        metadata
    FROM profiles
"""


def _row_to_profile(row: sqlite3.Row) -> Profile:
    return Profile.from_dict(
        {
            "profile_id": row["profile_id"],
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "display_name": row["display_name"],
            "fields": json.loads(row["fields"] or "{}"),
            "completeness": row["completeness"],
            "computed_at": row["computed_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
    )


class SqliteProfileQuery:
    """
    Read-only implementation of ProfileQueryService.

    - Never mutates profile records.
    - Returns None when no profile exists for the given entity_id.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def get_profile(
        self,
        entity_id: EntityId,
    ) -> Profile | None:
        """Return the Profile for the given entity, or None."""
        cursor = self._db.connection.execute(
            _SELECT_PROFILE + """
            WHERE entity_id = ?
            """,
            (str(entity_id),),
        )
        row: sqlite3.Row | None = cursor.fetchone()
        return _row_to_profile(row) if row is not None else None
