from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.guards import require
from core.identifiers import generate_knowledge_build_result_id
from core.time import utcnow
from core.types import EntityId, KnowledgeBuildResultId
from knowledge.conflict import Conflict
from knowledge.evidence import Evidence
from knowledge.fact import Fact
from knowledge.fact_evidence import FactEvidence
from knowledge.provenance import Provenance


@dataclass(frozen=True)
class KnowledgeBuildResult:
    result_id: KnowledgeBuildResultId
    entity_id: EntityId
    facts: tuple[Fact, ...]
    evidence: tuple[Evidence, ...]
    fact_evidence_links: tuple[FactEvidence, ...]
    provenance_records: tuple[Provenance, ...]
    conflicts: tuple[Conflict, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        require(
            isinstance(self.result_id, str) and bool(self.result_id.strip()),
            "result_id must be a non-empty string",
        )
        require(
            isinstance(self.entity_id, str) and bool(self.entity_id.strip()),
            "entity_id must be a non-empty string",
        )
        require(
            isinstance(self.facts, tuple),
            "facts must be a tuple",
        )
        require(
            all(isinstance(f, Fact) for f in self.facts),
            "all items in facts must be Fact instances",
        )

        fact_ids: frozenset[str] = frozenset(f.fact_id for f in self.facts)

        require(
            len(fact_ids) == len(self.facts),
            "fact ids must be unique within KnowledgeBuildResult",
        )
        require(
            isinstance(self.evidence, tuple),
            "evidence must be a tuple",
        )
        require(
            all(isinstance(e, Evidence) for e in self.evidence),
            "all items in evidence must be Evidence instances",
        )

        evidence_ids: frozenset[str] = frozenset(e.evidence_id for e in self.evidence)

        require(
            len(evidence_ids) == len(self.evidence),
            "evidence ids must be unique within KnowledgeBuildResult",
        )
        require(
            isinstance(self.fact_evidence_links, tuple),
            "fact_evidence_links must be a tuple",
        )
        require(
            all(isinstance(fe, FactEvidence) for fe in self.fact_evidence_links),
            "all items in fact_evidence_links must be FactEvidence instances",
        )

        for fe in self.fact_evidence_links:
            require(
                fe.fact_id in fact_ids,
                f"FactEvidence.fact_id '{fe.fact_id}' does not reference a Fact in this result",
            )
            require(
                fe.evidence_id in evidence_ids,
                f"FactEvidence.evidence_id '{fe.evidence_id}' does not reference an Evidence in this result",
            )

        require(
            isinstance(self.provenance_records, tuple),
            "provenance_records must be a tuple",
        )
        require(
            all(isinstance(p, Provenance) for p in self.provenance_records),
            "all items in provenance_records must be Provenance instances",
        )

        provenance_fact_ids: frozenset[str] = frozenset(
            p.fact_id for p in self.provenance_records
        )

        require(
            provenance_fact_ids == fact_ids,
            "provenance_records must cover every Fact exactly once — "
            f"missing: {fact_ids - provenance_fact_ids}, "
            f"unknown: {provenance_fact_ids - fact_ids}",
        )
        require(
            len(provenance_fact_ids) == len(self.provenance_records),
            "duplicate provenance records detected",
        )
        require(
            isinstance(self.conflicts, tuple),
            "conflicts must be a tuple",
        )
        require(
            all(isinstance(c, Conflict) for c in self.conflicts),
            "all items in conflicts must be Conflict instances",
        )

        for c in self.conflicts:
            for fid in c.fact_ids:
                require(
                    fid in fact_ids,
                    f"Conflict references fact_id '{fid}' which does not exist in this result",
                )

        require(
            isinstance(self.created_at, datetime),
            "created_at must be a datetime instance",
        )

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def provenance_count(self) -> int:
        return len(self.provenance_records)

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def has_facts(self) -> bool:
        return bool(self.facts)

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def evidence_for_fact(self, fact_id: str) -> tuple[Evidence, ...]:
        evidence_ids = frozenset(
            fe.evidence_id for fe in self.fact_evidence_links if fe.fact_id == fact_id
        )
        return tuple(e for e in self.evidence if e.evidence_id in evidence_ids)

    def facts_for_evidence(self, evidence_id: str) -> tuple[Fact, ...]:
        fact_ids = frozenset(
            fe.fact_id
            for fe in self.fact_evidence_links
            if fe.evidence_id == evidence_id
        )
        return tuple(f for f in self.facts if f.fact_id in fact_ids)

    def provenance_for_fact(self, fact_id: str) -> Provenance | None:
        for p in self.provenance_records:
            if p.fact_id == fact_id:
                return p
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "result_id": self.result_id,
            "entity_id": self.entity_id,
            "facts": [f.to_dict() for f in self.facts],
            "evidence": [e.to_dict() for e in self.evidence],
            "fact_evidence_links": [fe.to_dict() for fe in self.fact_evidence_links],
            "provenance_records": [p.to_dict() for p in self.provenance_records],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def create(
        cls,
        entity_id: EntityId,
        facts: tuple[Fact, ...],
        evidence: tuple[Evidence, ...],
        fact_evidence_links: tuple[FactEvidence, ...],
        provenance_records: tuple[Provenance, ...],
        conflicts: tuple[Conflict, ...],
    ) -> KnowledgeBuildResult:
        return cls(
            result_id=generate_knowledge_build_result_id(),
            entity_id=entity_id,
            facts=facts,
            evidence=evidence,
            fact_evidence_links=fact_evidence_links,
            provenance_records=provenance_records,
            conflicts=conflicts,
            created_at=utcnow(),
        )
