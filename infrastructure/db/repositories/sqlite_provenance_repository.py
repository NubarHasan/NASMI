from __future__ import annotations

import sqlite3
from typing import Any

from application.ports.provenance_repository import ProvenanceRepository
from core.types import EntityId, FactId, ProvenanceId
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.sqlite_helpers import (
    deserialize_json,
    row_to_dict,
    serialize_json,
)
from knowledge.provenance import Provenance, ProvenanceStep


class SqliteProvenanceRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    @staticmethod
    def _row_to_provenance(row: sqlite3.Row) -> Provenance:
        d: dict[str, Any] = row_to_dict(row)
        steps = tuple(
            ProvenanceStep.from_dict(s)
            for s in (deserialize_json(d["decision_chain"]) or [])
        )
        return Provenance(
            provenance_id=ProvenanceId(d["provenance_id"]),
            fact_id=FactId(d["fact_id"]),
            entity_id=EntityId(d["entity_id"]),
            decision_chain=steps,
            summary=d["summary"],
            created_at=d["created_at"],
        )

    def save(self, provenance: Provenance) -> None:
        sql = """
            INSERT INTO provenance (
                provenance_id,
                fact_id,
                entity_id,
                decision_chain,
                summary,
                created_at
            ) VALUES (
                :provenance_id,
                :fact_id,
                :entity_id,
                :decision_chain,
                :summary,
                :created_at
            )
            ON CONFLICT(provenance_id) DO UPDATE SET
                decision_chain = excluded.decision_chain,
                summary        = excluded.summary
        """
        d = provenance.to_dict()
        params: dict[str, Any] = {
            "provenance_id": d["provenance_id"],
            "fact_id": d["fact_id"],
            "entity_id": d["entity_id"],
            "decision_chain": serialize_json(d["decision_chain"]),
            "summary": d["summary"],
            "created_at": d["created_at"],
        }
        self._conn.execute(sql, params)

    def get(self, provenance_id: ProvenanceId) -> Provenance | None:
        sql = "SELECT * FROM provenance WHERE provenance_id = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (provenance_id,)).fetchone()
        return self._row_to_provenance(row) if row else None

    def exists(self, provenance_id: ProvenanceId) -> bool:
        sql = "SELECT 1 FROM provenance WHERE provenance_id = ? LIMIT 1"
        return self._conn.execute(sql, (provenance_id,)).fetchone() is not None

    def get_by_fact(self, fact_id: FactId) -> Provenance | None:
        sql = "SELECT * FROM provenance WHERE fact_id = ?"
        row = self._conn.execute(sql, (fact_id,)).fetchone()
        return self._row_to_provenance(row) if row else None

    def list_by_entity(self, entity_id: EntityId) -> tuple[Provenance, ...]:
        sql = "SELECT * FROM provenance WHERE entity_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (entity_id,)).fetchall()
        return tuple(self._row_to_provenance(r) for r in rows)


def _assert_protocol() -> None:
    _: ProvenanceRepository = SqliteProvenanceRepository.__new__(
        SqliteProvenanceRepository
    )


_assert_protocol()
