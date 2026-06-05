from __future__ import annotations

import sqlite3
from typing import Any

from application.ports.evidence_repository import EvidenceRepository
from core.types import DocumentId, EntityId, EvidenceId, SourceId
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.sqlite_helpers import (
    deserialize_json,
    row_to_dict,
    serialize_json,
)
from knowledge.evidence import Evidence


class SqliteEvidenceRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    @staticmethod
    def _row_to_evidence(row: sqlite3.Row) -> Evidence:
        d: dict[str, Any] = row_to_dict(row)
        return Evidence(
            evidence_id=EvidenceId(d["evidence_id"]),
            source_id=SourceId(d["source_id"]),
            entity_id=EntityId(d["entity_id"]),
            field_name=d["field_name"],
            raw_value=d["raw_value"],
            extraction_method=d["extraction_method"],
            confidence=float(d["confidence"]),
            created_at=d["created_at"],
            location=deserialize_json(d.get("location")) or {},
            metadata=deserialize_json(d.get("metadata")) or {},
        )

    def save(self, evidence: Evidence) -> None:
        sql = """
            INSERT INTO evidence (
                evidence_id,
                source_id,
                entity_id,
                field_name,
                raw_value,
                extraction_method,
                confidence,
                created_at,
                location,
                metadata
            ) VALUES (
                :evidence_id,
                :source_id,
                :entity_id,
                :field_name,
                :raw_value,
                :extraction_method,
                :confidence,
                :created_at,
                :location,
                :metadata
            )
            ON CONFLICT(evidence_id) DO UPDATE SET
                source_id         = excluded.source_id,
                entity_id         = excluded.entity_id,
                field_name        = excluded.field_name,
                raw_value         = excluded.raw_value,
                extraction_method = excluded.extraction_method,
                confidence        = excluded.confidence,
                location          = excluded.location,
                metadata          = excluded.metadata
        """
        params: dict[str, Any] = {
            "evidence_id": evidence.evidence_id,
            "source_id": evidence.source_id,
            "entity_id": evidence.entity_id,
            "field_name": evidence.field_name,
            "raw_value": evidence.raw_value,
            "extraction_method": evidence.extraction_method,
            "confidence": evidence.confidence,
            "created_at": evidence.created_at,
            "location": serialize_json(evidence.location),
            "metadata": serialize_json(evidence.metadata),
        }
        self._conn.execute(sql, params)

    def get(self, evidence_id: EvidenceId) -> Evidence | None:
        sql = "SELECT * FROM evidence WHERE evidence_id = ?"
        row: sqlite3.Row | None = self._conn.execute(sql, (evidence_id,)).fetchone()
        return self._row_to_evidence(row) if row else None

    def exists(self, evidence_id: EvidenceId) -> bool:
        sql = "SELECT 1 FROM evidence WHERE evidence_id = ? LIMIT 1"
        return self._conn.execute(sql, (evidence_id,)).fetchone() is not None

    def list_by_entity(self, entity_id: EntityId) -> tuple[Evidence, ...]:
        sql = "SELECT * FROM evidence WHERE entity_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (entity_id,)).fetchall()
        return tuple(self._row_to_evidence(r) for r in rows)

    def list_by_source(self, source_id: SourceId) -> tuple[Evidence, ...]:
        sql = "SELECT * FROM evidence WHERE source_id = ? ORDER BY created_at"
        rows: list[sqlite3.Row] = self._conn.execute(sql, (source_id,)).fetchall()
        return tuple(self._row_to_evidence(r) for r in rows)

    def list_by_document(self, document_id: DocumentId) -> tuple[Evidence, ...]:
        sql = """
            SELECT e.*
            FROM evidence e
            JOIN sources s ON s.source_id = e.source_id
            WHERE s.document_id = ?
            ORDER BY e.created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(sql, (document_id,)).fetchall()
        return tuple(self._row_to_evidence(r) for r in rows)

    def list_by_field(
        self,
        entity_id: EntityId,
        field_name: str,
    ) -> tuple[Evidence, ...]:
        sql = """
            SELECT * FROM evidence
            WHERE entity_id = ? AND field_name = ?
            ORDER BY created_at
        """
        rows: list[sqlite3.Row] = self._conn.execute(
            sql, (entity_id, field_name)
        ).fetchall()
        return tuple(self._row_to_evidence(r) for r in rows)


def _assert_protocol() -> None:
    _: EvidenceRepository = SqliteEvidenceRepository.__new__(SqliteEvidenceRepository)


_assert_protocol()
