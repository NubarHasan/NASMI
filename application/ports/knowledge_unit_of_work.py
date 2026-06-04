from __future__ import annotations

from typing import Protocol

from application.ports.conflict_repository import ConflictRepository
from application.ports.document_repository import DocumentRepository
from application.ports.evidence_repository import EvidenceRepository
from application.ports.fact_evidence_repository import FactEvidenceRepository
from application.ports.fact_repository import FactRepository
from application.ports.provenance_repository import ProvenanceRepository


class KnowledgeUnitOfWork(Protocol):

    facts: FactRepository
    evidence: EvidenceRepository
    fact_evidence: FactEvidenceRepository
    provenance: ProvenanceRepository
    conflicts: ConflictRepository
    documents: DocumentRepository

    def __enter__(self) -> KnowledgeUnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
