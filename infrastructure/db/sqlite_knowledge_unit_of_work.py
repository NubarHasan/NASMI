from __future__ import annotations

from application.ports.conflict_repository import ConflictRepository
from application.ports.document_repository import DocumentRepository
from application.ports.entity_repository import EntityRepository
from application.ports.evidence_repository import EvidenceRepository
from application.ports.fact_evidence_repository import FactEvidenceRepository
from application.ports.fact_repository import FactRepository
from application.ports.knowledge_unit_of_work import KnowledgeUnitOfWork
from application.ports.provenance_repository import ProvenanceRepository
from application.ports.source_repository import SourceRepository
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
from infrastructure.db.repositories.sqlite_source_repository import (
    SqliteSourceRepository,
)


class SqliteKnowledgeUnitOfWork:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self.facts: FactRepository = SqliteFactRepository(db)
        self.evidence: EvidenceRepository = SqliteEvidenceRepository(db)
        self.fact_evidence: FactEvidenceRepository = SqliteFactEvidenceRepository(db)
        self.provenance: ProvenanceRepository = SqliteProvenanceRepository(db)
        self.conflicts: ConflictRepository = SqliteConflictRepository(db)
        self.documents: DocumentRepository = SqliteDocumentRepository(db)
        self.entities: EntityRepository = SqliteEntityRepository(db)
        self.sources: SourceRepository = SqliteSourceRepository(db)

    def __enter__(self) -> KnowledgeUnitOfWork:
        return self

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
