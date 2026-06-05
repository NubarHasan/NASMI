from __future__ import annotations

from application.ports.knowledge_unit_of_work import KnowledgeUnitOfWork
from infrastructure.db.connection import DatabaseConnection
from infrastructure.db.repositories.sqlite_conflict_repository import (
    SqliteConflictRepository,
)
from infrastructure.db.repositories.sqlite_document_repository import (
    SqliteDocumentRepository,
)
from infrastructure.db.repositories.sqlite_entity_repository import (
    SqliteEntityRepository,
)
from infrastructure.db.repositories.sqlite_evidence_repository import (
    SqliteEvidenceRepository,
)
from infrastructure.db.repositories.sqlite_fact_evidence_repository import (
    SqliteFactEvidenceRepository,
)
from infrastructure.db.repositories.sqlite_fact_repository import SqliteFactRepository
from infrastructure.db.repositories.sqlite_provenance_repository import (
    SqliteProvenanceRepository,
)


class SqliteKnowledgeUnitOfWork:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self.facts = SqliteFactRepository(db)
        self.evidence = SqliteEvidenceRepository(db)
        self.fact_evidence = SqliteFactEvidenceRepository(db)
        self.provenance = SqliteProvenanceRepository(db)
        self.conflicts = SqliteConflictRepository(db)
        self.documents = SqliteDocumentRepository(db)
        self.entities = SqliteEntityRepository(db)

    def __enter__(self) -> KnowledgeUnitOfWork:
        return self  # type: ignore[return-value]

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self._db.connection.commit()

    def rollback(self) -> None:
        self._db.connection.rollback()
