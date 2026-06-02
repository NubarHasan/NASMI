from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from core.guards import require
from core.identifiers import (
    is_valid_conflict_id,
    is_valid_entity_id,
    is_valid_fact_id,
)
from core.types import ConflictId, EntityId, EvidenceId, FactId
from knowledge.conflict import Conflict, ConflictStatus
from knowledge.entity import Entity
from knowledge.evidence import Evidence
from knowledge.fact import Fact, FactStatus
from knowledge.fact_evidence import FactEvidence, FactEvidenceRole
from knowledge.profile import Profile, ProfileField
from knowledge.provenance import Provenance

_SYSTEM_ACTOR: Final[str] = "system"


@dataclass
class _KnowledgeStore:
    _entities: dict[EntityId, Entity] = field(default_factory=dict)
    _facts: dict[FactId, Fact] = field(default_factory=dict)
    _evidence: dict[EvidenceId, Evidence] = field(default_factory=dict)
    _fact_evidence: list[FactEvidence] = field(default_factory=list)
    _conflicts: dict[ConflictId, Conflict] = field(default_factory=dict)
    _provenance: dict[FactId, Provenance] = field(default_factory=dict)


class KnowledgeService:

    def __init__(self) -> None:
        self._store = _KnowledgeStore()

    def register_entity(self, entity: Entity) -> Entity:
        require(isinstance(entity, Entity), "entity must be an Entity")
        require(
            entity.entity_id not in self._store._entities,
            f"entity {entity.entity_id!r} already registered",
        )
        self._store._entities[entity.entity_id] = entity
        return entity

    def get_entity(self, entity_id: EntityId) -> Entity | None:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return self._store._entities.get(entity_id)

    def list_entities(self) -> tuple[Entity, ...]:
        return tuple(self._store._entities.values())

    def register_evidence(self, evidence: Evidence) -> Evidence:
        require(isinstance(evidence, Evidence), "evidence must be an Evidence")
        require(
            evidence.evidence_id not in self._store._evidence,
            f"evidence {evidence.evidence_id!r} already registered",
        )
        self._store._evidence[evidence.evidence_id] = evidence
        return evidence

    def list_evidence(self, entity_id: EntityId) -> tuple[Evidence, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(
            e for e in self._store._evidence.values() if e.entity_id == entity_id
        )

    def list_evidence_for_field(
        self,
        entity_id: EntityId,
        field_name: str,
    ) -> tuple[Evidence, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(bool(field_name.strip()), "field_name must not be blank")
        return tuple(
            e
            for e in self._store._evidence.values()
            if e.entity_id == entity_id and e.field_name == field_name
        )

    def submit_fact(self, fact: Fact) -> Fact:
        require(isinstance(fact, Fact), "fact must be a Fact")
        require(
            fact.status == FactStatus.PENDING,
            "submitted fact must have PENDING status",
        )
        require(
            fact.fact_id not in self._store._facts,
            f"fact {fact.fact_id!r} already exists",
        )
        self._store._facts[fact.fact_id] = fact
        return fact

    def get_fact(self, fact_id: FactId) -> Fact | None:
        require(is_valid_fact_id(fact_id), "invalid fact_id")
        return self._store._facts.get(fact_id)

    def list_facts_by_entity(self, entity_id: EntityId) -> tuple[Fact, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(f for f in self._store._facts.values() if f.entity_id == entity_id)

    def list_accepted_facts(self, entity_id: EntityId) -> tuple[Fact, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(
            f
            for f in self._store._facts.values()
            if f.entity_id == entity_id and f.status == FactStatus.ACCEPTED
        )

    def link_fact_evidence(self, fact_evidence: FactEvidence) -> FactEvidence:
        require(
            isinstance(fact_evidence, FactEvidence),
            "fact_evidence must be a FactEvidence",
        )
        require(
            fact_evidence.fact_id in self._store._facts,
            f"fact {fact_evidence.fact_id!r} not found",
        )
        require(
            fact_evidence.evidence_id in self._store._evidence,
            f"evidence {fact_evidence.evidence_id!r} not found",
        )
        require(
            not any(
                fe.fact_id == fact_evidence.fact_id
                and fe.evidence_id == fact_evidence.evidence_id
                and fe.role == fact_evidence.role
                for fe in self._store._fact_evidence
            ),
            "fact-evidence relationship already exists",
        )
        self._store._fact_evidence.append(fact_evidence)
        return fact_evidence

    def list_fact_evidence(self, fact_id: FactId) -> tuple[FactEvidence, ...]:
        require(is_valid_fact_id(fact_id), "invalid fact_id")
        return tuple(fe for fe in self._store._fact_evidence if fe.fact_id == fact_id)

    def accept_fact(
        self,
        fact_id: FactId,
        accepted_by: str = _SYSTEM_ACTOR,
    ) -> Fact | Conflict:
        require(is_valid_fact_id(fact_id), "invalid fact_id")
        require(bool(accepted_by.strip()), "accepted_by must not be blank")

        fact = self._store._facts.get(fact_id)
        require(fact is not None, f"fact {fact_id!r} not found")
        require(fact.status == FactStatus.PENDING, f"fact {fact_id!r} is not PENDING")

        accepted = self._find_accepted_fact(fact.entity_id, fact.field_name)

        if accepted is None:
            return self._mark_accepted(fact, accepted_by)

        if self._values_match(accepted, fact):
            self._link_corroborating_evidence(accepted, fact)
            rejected = fact.reject()
            self._store._facts[fact_id] = rejected
            return rejected

        return self._open_conflict(accepted, fact)

    def reject_fact(self, fact_id: FactId) -> Fact:
        require(is_valid_fact_id(fact_id), "invalid fact_id")

        fact = self._store._facts.get(fact_id)
        require(fact is not None, f"fact {fact_id!r} not found")
        require(fact.status == FactStatus.PENDING, "only PENDING facts can be rejected")

        rejected = fact.reject()
        self._store._facts[fact_id] = rejected
        return rejected

    def list_conflicts(self, entity_id: EntityId) -> tuple[Conflict, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(
            c for c in self._store._conflicts.values() if c.entity_id == entity_id
        )

    def list_conflicts_by_status(
        self,
        entity_id: EntityId,
        status: ConflictStatus,
    ) -> tuple[Conflict, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(isinstance(status, ConflictStatus), "invalid status")
        return tuple(
            c
            for c in self._store._conflicts.values()
            if c.entity_id == entity_id and c.status == status
        )

    def resolve_conflict(
        self,
        conflict_id: ConflictId,
        winning_fact_id: FactId,
        resolved_by: str,
        resolution_note: str = "",
    ) -> Conflict:
        require(is_valid_conflict_id(conflict_id), "invalid conflict_id")
        require(is_valid_fact_id(winning_fact_id), "invalid winning_fact_id")
        require(bool(resolved_by.strip()), "resolved_by must not be blank")

        conflict = self._store._conflicts.get(conflict_id)
        require(conflict is not None, f"conflict {conflict_id!r} not found")
        require(conflict.is_open, f"conflict {conflict_id!r} is not OPEN")
        require(
            winning_fact_id in conflict.fact_ids,
            f"winning_fact_id {winning_fact_id!r} not part of this conflict",
        )

        for fid in conflict.fact_ids:
            fact = self._store._facts.get(fid)
            if fact is None:
                continue
            if fid == winning_fact_id:
                if fact.status == FactStatus.PENDING:
                    self._store._facts[fid] = fact.accept(accepted_by=resolved_by)
            else:
                self._store._facts[fid] = fact.supersede(new_fact_id=winning_fact_id)

        resolved = conflict.resolve(
            resolved_fact_id=winning_fact_id,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
        )
        self._store._conflicts[conflict_id] = resolved
        return resolved

    def dismiss_conflict(
        self,
        conflict_id: ConflictId,
        resolved_by: str,
        resolution_note: str = "",
    ) -> Conflict:
        require(is_valid_conflict_id(conflict_id), "invalid conflict_id")
        require(bool(resolved_by.strip()), "resolved_by must not be blank")

        conflict = self._store._conflicts.get(conflict_id)
        require(conflict is not None, f"conflict {conflict_id!r} not found")
        require(conflict.is_open, f"conflict {conflict_id!r} is not OPEN")

        dismissed = conflict.dismiss(
            resolved_by=resolved_by,
            resolution_note=resolution_note,
        )
        self._store._conflicts[conflict_id] = dismissed
        return dismissed

    def record_provenance(self, provenance: Provenance) -> Provenance:
        require(isinstance(provenance, Provenance), "provenance must be a Provenance")
        require(is_valid_fact_id(provenance.fact_id), "provenance has invalid fact_id")
        self._store._provenance[provenance.fact_id] = provenance
        return provenance

    def list_provenance(self, entity_id: EntityId) -> tuple[Provenance, ...]:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        return tuple(
            p for p in self._store._provenance.values() if p.entity_id == entity_id
        )

    def get_provenance_by_fact(self, fact_id: FactId) -> Provenance | None:
        require(is_valid_fact_id(fact_id), "invalid fact_id")
        return self._store._provenance.get(fact_id)

    def build_profile(
        self,
        entity_id: EntityId,
        entity_type: str,
        display_name: str,
        metadata: dict | None = None,
    ) -> Profile:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(bool(entity_type.strip()), "entity_type must not be blank")
        require(bool(display_name.strip()), "display_name must not be blank")

        accepted = self.list_accepted_facts(entity_id)
        fields: dict[str, ProfileField] = {}

        for fact in accepted:
            fields[fact.field_name] = ProfileField(
                field_name=fact.field_name,
                value=fact.canonical_value,
                display_value=fact.display_value,
                confidence=fact.confidence,
                fact_id=fact.fact_id,
                sourced_at=fact.accepted_at or fact.created_at,
            )

        return Profile.create(
            entity_id=entity_id,
            entity_type=entity_type,
            display_name=display_name,
            fields=fields,
            completeness=1.0,
            metadata=metadata,
        )

    def _find_accepted_fact(
        self,
        entity_id: EntityId,
        field_name: str,
    ) -> Fact | None:
        for fact in self._store._facts.values():
            if (
                fact.entity_id == entity_id
                and fact.field_name == field_name
                and fact.status == FactStatus.ACCEPTED
            ):
                return fact
        return None

    def _values_match(self, existing: Fact, incoming: Fact) -> bool:
        return (
            existing.canonical_value == incoming.canonical_value
            and existing.value_type == incoming.value_type
        )

    def _mark_accepted(self, fact: Fact, accepted_by: str) -> Fact:
        accepted = fact.accept(accepted_by=accepted_by)
        self._store._facts[fact.fact_id] = accepted
        return accepted

    def _link_corroborating_evidence(
        self,
        accepted: Fact,
        duplicate: Fact,
    ) -> None:
        incoming_evidence = tuple(
            fe for fe in self._store._fact_evidence if fe.fact_id == duplicate.fact_id
        )
        for fe in incoming_evidence:
            already_linked = any(
                x.fact_id == accepted.fact_id
                and x.evidence_id == fe.evidence_id
                and x.role == FactEvidenceRole.CORROBORATING
                for x in self._store._fact_evidence
            )
            if not already_linked:
                corroborating = FactEvidence.create(
                    fact_id=accepted.fact_id,
                    evidence_id=fe.evidence_id,
                    role=FactEvidenceRole.CORROBORATING,
                )
                self._store._fact_evidence.append(corroborating)

    def _open_conflict(
        self,
        accepted: Fact,
        incoming: Fact,
    ) -> Conflict:
        conflict = Conflict.create(
            entity_id=accepted.entity_id,
            field_name=accepted.field_name,
            fact_ids=[accepted.fact_id, incoming.fact_id],
        )
        self._store._conflicts[conflict.conflict_id] = conflict
        return conflict
