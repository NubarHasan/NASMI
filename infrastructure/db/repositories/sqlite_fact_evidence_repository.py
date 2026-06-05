from __future__ import annotations

import sqlite3

from application.ports.fact_evidence_repository import FactEvidenceRepository
from core.types import EvidenceId, FactId
from infrastructure.db.connection import DatabaseConnection
from knowledge.fact_evidence import FactEvidence


class SqliteFactEvidenceRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, link: FactEvidence) -> None:
        sql = """
            INSERT INTO fact_evidence (
                fact_evidence_id,
                fact_id,
                evidence_id,
                role,
                created_at
            ) VALUES (
                :fact_evidence_id,
                :fact_id,
                :evidence_id,
                :role,
                :created_at
            )
            ON CONFLICT(fact_id, evidence_id) DO NOTHING
        """
        self._conn.execute(sql, link.to_dict())

    def exists(
        self,
        fact_id: FactId,
        evidence_id: EvidenceId,
    ) -> bool:
        sql = """
            SELECT 1
            FROM fact_evidence
            WHERE fact_id = ? AND evidence_id = ?
            LIMIT 1
        """
        return self._conn.execute(sql, (fact_id, evidence_id)).fetchone() is not None

    def list_evidence_ids(
        self,
        fact_id: FactId,
    ) -> tuple[EvidenceId, ...]:
        sql = """
            SELECT evidence_id
            FROM fact_evidence
            WHERE fact_id = ?
            ORDER BY created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(sql, (fact_id,)).fetchall()
        return tuple(EvidenceId(r[0]) for r in rows)

    def list_fact_ids(
        self,
        evidence_id: EvidenceId,
    ) -> tuple[FactId, ...]:
        sql = """
            SELECT fact_id
            FROM fact_evidence
            WHERE evidence_id = ?
            ORDER BY created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(sql, (evidence_id,)).fetchall()
        return tuple(FactId(r[0]) for r in rows)


def _assert_protocol() -> None:
    _: FactEvidenceRepository = SqliteFactEvidenceRepository.__new__(
        SqliteFactEvidenceRepository
    )


_assert_protocol()
