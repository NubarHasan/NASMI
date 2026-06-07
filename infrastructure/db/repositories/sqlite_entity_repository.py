from __future__ import annotations

import sqlite3
from typing import Any

from application.ports.entity_repository import EntityRepository
from core.types import EntityId
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.sqlite_helpers import (
    deserialize_json,
    row_to_dict,
    serialize_json,
)
from knowledge.entity import Entity, EntityStatus, EntityType


class SqliteEntityRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    @staticmethod
    def _row_to_entity(row: sqlite3.Row) -> Entity:
        d: dict[str, Any] = row_to_dict(row)
        return Entity(
            entity_id=EntityId(d["entity_id"]),
            entity_type=d["entity_type"],
            display_name=d["display_name"],
            status=EntityStatus(d["status"]),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            primary_language=d.get("primary_language"),
            merged_into=(EntityId(d["merged_into"]) if d.get("merged_into") else None),
            metadata=deserialize_json(d.get("metadata")) or {},
        )

    def save(self, entity: Entity) -> None:
        sql = """
            INSERT INTO entities (
                entity_id,
                entity_type,
                display_name,
                status,
                created_at,
                updated_at,
                primary_language,
                merged_into,
                metadata
            ) VALUES (
                :entity_id,
                :entity_type,
                :display_name,
                :status,
                :created_at,
                :updated_at,
                :primary_language,
                :merged_into,
                :metadata
            )
            ON CONFLICT(entity_id) DO UPDATE SET
                entity_type      = excluded.entity_type,
                display_name     = excluded.display_name,
                status           = excluded.status,
                updated_at       = excluded.updated_at,
                primary_language = excluded.primary_language,
                merged_into      = excluded.merged_into,
                metadata         = excluded.metadata
        """
        params: dict[str, Any] = {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "display_name": entity.display_name,
            "status": str(entity.status),
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "primary_language": entity.primary_language,
            "merged_into": entity.merged_into,
            "metadata": serialize_json(entity.metadata),
        }
        self._conn.execute(sql, params)
        self._conn.commit()

    def get(self, entity_id: EntityId) -> Entity | None:
        sql = "SELECT * FROM entities WHERE entity_id = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (entity_id,)).fetchone()
        return self._row_to_entity(row) if row else None

    def exists(self, entity_id: EntityId) -> bool:
        sql = "SELECT 1 FROM entities WHERE entity_id = ? LIMIT 1"
        return self._conn.execute(sql, (entity_id,)).fetchone() is not None

    def list_by_type(self, entity_type: EntityType) -> tuple[Entity, ...]:
        sql = "SELECT * FROM entities WHERE entity_type = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (entity_type,)).fetchall()
        return tuple(self._row_to_entity(r) for r in rows)


def _assert_protocol() -> None:
    _: EntityRepository = SqliteEntityRepository.__new__(SqliteEntityRepository)


_assert_protocol()
