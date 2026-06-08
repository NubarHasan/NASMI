from __future__ import annotations

import re
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
            existing_keys = self._load_existing_fact_keys(uow, facts)
            kept_facts, skipped_fact_ids = self._deduplicate_facts(facts, existing_keys)

            kept_fact_ids = {
                str(self._get_attr(fact, "fact_id"))
                for fact in kept_facts
                if self._get_attr(fact, "fact_id") is not None
            }

            kept_links = [
                link
                for link in fact_evidence_links
                if self._belongs_to_kept_fact(link, kept_fact_ids, skipped_fact_ids)
            ]

            kept_evidence_ids = {
                str(self._get_attr(link, "evidence_id"))
                for link in kept_links
                if self._get_attr(link, "evidence_id") is not None
            }

            kept_evidence = [
                evidence
                for evidence in evidence_list
                if str(self._get_attr(evidence, "evidence_id")) in kept_evidence_ids
            ]

            kept_provenance = [
                provenance
                for provenance in provenance_list
                if self._belongs_to_kept_fact(
                    provenance,
                    kept_fact_ids,
                    skipped_fact_ids,
                )
            ]

            kept_conflicts = [
                conflict
                for conflict in conflicts
                if self._belongs_to_kept_fact(conflict, kept_fact_ids, skipped_fact_ids)
            ]

            self._ensure_sources(uow, kept_facts, kept_evidence)

            for fact in kept_facts:
                uow.facts.save(fact)

            for evidence in kept_evidence:
                uow.evidence.save(evidence)

            for link in kept_links:
                uow.fact_evidence.save(link)

            for provenance in kept_provenance:
                uow.provenance.save(provenance)

            for conflict in kept_conflicts:
                uow.conflicts.save(conflict)

            uow.commit()

    def _load_existing_fact_keys(
        self,
        uow: KnowledgeUnitOfWork,
        facts: list[Fact],
    ) -> set[tuple[str, str, str]]:
        keys: set[tuple[str, str, str]] = set()

        entity_ids = {
            EntityId(str(self._get_attr(fact, "entity_id")))
            for fact in facts
            if self._get_attr(fact, "entity_id") is not None
        }

        for entity_id in entity_ids:
            existing_facts = uow.facts.list_by_entity(entity_id)
            for existing_fact in existing_facts:
                key = self._fact_key(existing_fact)
                if key is not None:
                    keys.add(key)

        return keys

    def _deduplicate_facts(
        self,
        facts: list[Fact],
        existing_keys: set[tuple[str, str, str]],
    ) -> tuple[list[Fact], set[str]]:
        kept: list[Fact] = []
        skipped_fact_ids: set[str] = set()
        seen_keys = set(existing_keys)

        for fact in facts:
            fact_id = self._get_attr(fact, "fact_id")
            key = self._fact_key(fact)

            if key is None:
                kept.append(fact)
                continue

            if key in seen_keys:
                if fact_id is not None:
                    skipped_fact_ids.add(str(fact_id))
                continue

            seen_keys.add(key)
            kept.append(fact)

        return kept, skipped_fact_ids

    def _fact_key(self, fact: Any) -> tuple[str, str, str] | None:
        entity_id = self._get_attr(fact, "entity_id")
        field_name = self._get_attr(fact, "field_name")
        canonical_value = self._get_attr(fact, "canonical_value")

        if canonical_value is None:
            canonical_value = self._get_attr(fact, "display_value")

        if entity_id is None or field_name is None or canonical_value is None:
            return None

        normalized_entity = str(entity_id).strip()
        normalized_field = self._normalize_field_name_for_dedup(str(field_name))
        normalized_value = self._normalize_value_for_dedup(
            value=str(canonical_value),
            field_name=normalized_field,
        )

        if not normalized_entity or not normalized_field or not normalized_value:
            return None

        return normalized_entity, normalized_field, normalized_value

    def _normalize_field_name_for_dedup(self, field_name: str) -> str:
        field = " ".join(str(field_name).strip().lower().split())

        aliases = {
            "date": "date_of_birth",
            "birth_date": "date_of_birth",
            "date_birth": "date_of_birth",
            "dob": "date_of_birth",
            "date_of_birth": "date_of_birth",
            "expiry": "expiry_date",
            "expiry_date": "expiry_date",
            "expiration_date": "expiry_date",
            "valid_until": "expiry_date",
            "valid_to": "expiry_date",
            "issue": "issue_date",
            "issued_date": "issue_date",
            "date_of_issue": "issue_date",
            "issue_date": "issue_date",
            "given_name": "given_names",
            "given_names": "given_names",
            "first_name": "given_names",
            "firstname": "given_names",
            "forename": "given_names",
            "surname": "surname",
            "last_name": "surname",
            "lastname": "surname",
            "family_name": "surname",
            "email_address": "email",
            "e-mail": "email",
            "mail": "email",
            "phone": "phone_number",
            "phone_number": "phone_number",
            "telephone": "phone_number",
            "mobile": "phone_number",
            "mobile_number": "phone_number",
        }

        return aliases.get(field, field)

    def _normalize_value_for_dedup(self, value: str, field_name: str) -> str:
        text = " ".join(str(value).strip().lower().split())

        if field_name in {"phone_number"}:
            return self._normalize_phone_value(text)

        if field_name in {"email"}:
            return text.replace(" ", "")

        if field_name in {"date_of_birth", "issue_date", "expiry_date", "date"}:
            return self._normalize_date_value(text)

        return text

    def _normalize_phone_value(self, value: str) -> str:
        text = str(value).strip()
        if text.startswith("+"):
            return "+" + re.sub(r"\D", "", text[1:])
        return re.sub(r"\D", "", text)

    def _normalize_date_value(self, value: str) -> str:
        text = str(value).strip().lower()
        match = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$", text)
        if match:
            day, month, year = match.groups()
            if len(year) == 2:
                year = "19" + year if int(year) > 30 else "20" + year
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"

        match = re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$", text)
        if match:
            year, month, day = match.groups()
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"

        digits = re.sub(r"\D", "", text)

        if len(digits) == 8:
            if digits[:4].isdigit() and 1900 <= int(digits[:4]) <= 2100:
                return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
            return f"{digits[4:8]}-{digits[2:4]}-{digits[0:2]}"

        if len(digits) == 6:
            day = digits[0:2]
            month = digits[2:4]
            year = digits[4:6]
            full_year = "19" + year if int(year) > 30 else "20" + year
            return f"{full_year}-{month}-{day}"

        return text

    def _belongs_to_kept_fact(
        self,
        obj: Any,
        kept_fact_ids: set[str],
        skipped_fact_ids: set[str],
    ) -> bool:
        fact_id = self._get_attr(obj, "fact_id")

        if fact_id is not None:
            fact_id_value = str(fact_id)
            if fact_id_value in skipped_fact_ids:
                return False
            return fact_id_value in kept_fact_ids

        candidate_fact_id = self._get_attr(obj, "candidate_fact_id")
        if candidate_fact_id is not None:
            return True

        return True

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
