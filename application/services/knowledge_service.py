from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from application.ports.knowledge_unit_of_work import KnowledgeUnitOfWork
from archive.source import Source, SourceType
from core.guards import require
from core.identifiers import is_valid_entity_id, is_valid_fact_id
from core.types import DocumentId, EntityId, EvidenceId, FactId, SourceId
from knowledge.conflict import Conflict
from knowledge.evidence import Evidence
from knowledge.fact import Fact, FactStatus
from knowledge.fact_evidence import FactEvidence
from knowledge.provenance import Provenance


class KnowledgeApplicationService:

    def __init__(self, uow_factory: Callable[[], KnowledgeUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def persist_knowledge_build(
        self,
        facts: list[Fact],
        evidence_list: list[Evidence],
        fact_evidence_links: list[FactEvidence],
        provenance_list: list[Provenance],
        conflicts: list[Conflict],
    ) -> None:
        with self._uow_factory() as uow:
            self._ensure_sources(uow, facts, evidence_list)

            for fact in facts:
                uow.facts.save(fact)

            for evidence in evidence_list:
                uow.evidence.save(evidence)

            for link in fact_evidence_links:
                uow.fact_evidence.save(link)

            for provenance in provenance_list:
                uow.provenance.save(provenance)

            for conflict in conflicts:
                uow.conflicts.save(conflict)

            uow.commit()

    def _ensure_sources(
        self,
        uow: KnowledgeUnitOfWork,
        facts: list[Fact],
        evidence_list: list[Evidence],
    ) -> None:
        for evidence in evidence_list:
            source_id_value = self._get_attr(evidence, "source_id")
            entity_id_value = self._get_attr(evidence, "entity_id")

            if source_id_value is None or entity_id_value is None:
                continue

            source_id = SourceId(str(source_id_value))
            entity_id = EntityId(str(entity_id_value))

            if uow.sources.exists(source_id):
                continue

            document_id = self._find_document_id_for_entity(uow, entity_id)
            if document_id is None:
                document_id = self._infer_document_id_from_objects(facts)
            if document_id is None:
                continue

            source = Source(
                source_id=source_id,
                entity_id=entity_id,
                source_type=SourceType.DOCUMENT,
                created_at=datetime.now(UTC).isoformat(),
                document_id=document_id,
                metadata={"created_by": "knowledge_service_fallback"},
            )

            uow.sources.save(source)

    def _find_document_id_for_entity(
        self,
        uow: KnowledgeUnitOfWork,
        entity_id: EntityId,
    ) -> DocumentId | None:
        documents = uow.documents.list_by_entity(entity_id)
        if not documents:
            return None

        latest_document = documents[-1]
        document_id = self._get_attr(latest_document, "document_id")
        if document_id is None:
            return None

        return DocumentId(str(document_id))

    def _infer_document_id_from_objects(self, objects: list[Any]) -> DocumentId | None:
        for obj in objects:
            document_id = self._get_attr(obj, "document_id")
            if document_id is not None:
                return DocumentId(str(document_id))
        return None

    def _get_attr(self, obj: Any, name: str) -> Any:
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict):
            return obj.get(name)
        return None

    def get_entity(self, entity_id: EntityId) -> Any | None:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")

        with self._uow_factory() as uow:
            return uow.entities.get(entity_id)

    def list_facts_by_entity(self, entity_id: EntityId) -> list[Fact]:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")

        with self._uow_factory() as uow:
            return list(uow.facts.list_by_entity(entity_id))

    def list_evidence_ids(self, fact_id: FactId) -> list[EvidenceId]:
        require(is_valid_fact_id(fact_id), f"invalid fact_id: {fact_id!r}")

        with self._uow_factory() as uow:
            return list(uow.fact_evidence.list_evidence_ids(fact_id))

    def accept_fact(self, fact_id: FactId, accepted_by: str) -> Fact:
        require(is_valid_fact_id(fact_id), f"invalid fact_id: {fact_id!r}")
        require(
            isinstance(accepted_by, str) and bool(accepted_by.strip()),
            "accepted_by must be a non-empty string",
        )

        with self._uow_factory() as uow:
            fact = uow.facts.get(fact_id)
            require(fact is not None, f"fact not found: {fact_id!r}")
            assert fact is not None

            updated = fact.accept(accepted_by=accepted_by)
            uow.facts.save(updated)
            uow.commit()

            return updated

    def reject_fact(self, fact_id: FactId) -> Fact:
        require(is_valid_fact_id(fact_id), f"invalid fact_id: {fact_id!r}")

        with self._uow_factory() as uow:
            fact = uow.facts.get(fact_id)
            require(fact is not None, f"fact not found: {fact_id!r}")
            assert fact is not None

            updated = fact.reject()
            uow.facts.save(updated)
            uow.commit()

            return updated

    def list_accepted_facts(self, entity_id: EntityId) -> list[Fact]:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")

        with self._uow_factory() as uow:
            all_facts = uow.facts.list_by_entity(entity_id)
            return [f for f in all_facts if f.status is FactStatus.ACCEPTED]

    def list_pending_facts(self, entity_id: EntityId) -> list[Fact]:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")

        with self._uow_factory() as uow:
            all_facts = uow.facts.list_by_entity(entity_id)
            return [f for f in all_facts if f.status is FactStatus.PENDING]
