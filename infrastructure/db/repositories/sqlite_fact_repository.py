from __future__ import annotations

import sqlite3
from typing import Any

from application.ports.fact_repository import FactRepository
from core.types import EntityId, FactId
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.sqlite_helpers import (
    deserialize_json,
    row_to_dict,
    serialize_json,
)
from knowledge.fact import (
    Fact,
    FactStatus,
    ValueType,
    _deserialize_value,
    _serialize_value,
)


class SqliteFactRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    @staticmethod
    def _row_to_fact(row: sqlite3.Row) -> Fact:
        d: dict[str, Any] = row_to_dict(row)
        vtype = ValueType(d["value_type"])
        return Fact(
            fact_id=FactId(d["fact_id"]),
            entity_id=EntityId(d["entity_id"]),
            field_name=d["field_name"],
            canonical_value=_deserialize_value(d.get("canonical_value"), vtype),
            display_value=d["display_value"],
            value_type=vtype,
            confidence=float(d["confidence"]),
            status=FactStatus(d["status"]),
            source_stage=d["source_stage"],
            created_at=d["created_at"],
            accepted_at=d.get("accepted_at"),
            accepted_by=d.get("accepted_by"),
            superseded_by=(
                FactId(d["superseded_by"]) if d.get("superseded_by") else None
            ),
            metadata=deserialize_json(d.get("metadata")) or {},
        )

    def save(self, fact: Fact) -> None:
        sql = """
            INSERT INTO facts (
                fact_id,
                entity_id,
                field_name,
                canonical_value,
                display_value,
                value_type,
                confidence,
                status,
                source_stage,
                created_at,
                accepted_at,
                accepted_by,
                superseded_by,
                metadata
            ) VALUES (
                :fact_id,
                :entity_id,
                :field_name,
                :canonical_value,
                :display_value,
                :value_type,
                :confidence,
                :status,
                :source_stage,
                :created_at,
                :accepted_at,
                :accepted_by,
                :superseded_by,
                :metadata
            )
            ON CONFLICT(fact_id) DO UPDATE SET
                entity_id       = excluded.entity_id,
                field_name      = excluded.field_name,
                canonical_value = excluded.canonical_value,
                display_value   = excluded.display_value,
                value_type      = excluded.value_type,
                confidence      = excluded.confidence,
                status          = excluded.status,
                source_stage    = excluded.source_stage,
                accepted_at     = excluded.accepted_at,
                accepted_by     = excluded.accepted_by,
                superseded_by   = excluded.superseded_by,
                metadata        = excluded.metadata
        """
        params: dict[str, Any] = {
            "fact_id": fact.fact_id,
            "entity_id": fact.entity_id,
            "field_name": fact.field_name,
            "canonical_value": _serialize_value(fact.canonical_value, fact.value_type),
            "display_value": fact.display_value,
            "value_type": str(fact.value_type),
            "confidence": fact.confidence,
            "status": str(fact.status),
            "source_stage": fact.source_stage,
            "created_at": fact.created_at,
            "accepted_at": fact.accepted_at,
            "accepted_by": fact.accepted_by,
            "superseded_by": fact.superseded_by,
            "metadata": serialize_json(fact.metadata),
        }
        self._conn.execute(sql, params)

    def get(self, fact_id: FactId) -> Fact | None:
        sql = "SELECT * FROM facts WHERE fact_id = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (fact_id,)).fetchone()
        return self._row_to_fact(row) if row else None

    def exists(self, fact_id: FactId) -> bool:
        sql = "SELECT 1 FROM facts WHERE fact_id = ? LIMIT 1"
        return self._conn.execute(sql, (fact_id,)).fetchone() is not None

    def list_by_entity(self, entity_id: EntityId) -> tuple[Fact, ...]:
        sql = "SELECT * FROM facts WHERE entity_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (entity_id,)).fetchall()
        return tuple(self._row_to_fact(r) for r in rows)

    def list_by_entity_and_type(
        self,
        entity_id: EntityId,
        fact_type: str,
    ) -> tuple[Fact, ...]:
        sql = """
            SELECT * FROM facts
            WHERE entity_id = ? AND field_name = ?
            ORDER BY created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(
            sql, (entity_id, fact_type)
        ).fetchall()
        return tuple(self._row_to_fact(r) for r in rows)

    def list_by_status(
        self,
        entity_id: EntityId,
        status: FactStatus,
    ) -> tuple[Fact, ...]:
        sql = """
            SELECT * FROM facts
            WHERE entity_id = ? AND status = ?
            ORDER BY created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(
            sql, (entity_id, str(status))
        ).fetchall()
        return tuple(self._row_to_fact(r) for r in rows)


def _assert_protocol() -> None:
    _: FactRepository = SqliteFactRepository.__new__(SqliteFactRepository)


_assert_protocol()
