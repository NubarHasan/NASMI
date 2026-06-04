from __future__ import annotations

from core.guards import require
from core.types import CandidateFactId, EntityId
from knowledge.conflict import Conflict
from knowledge.evidence import Evidence
from knowledge.fact import Fact
from knowledge.fact_evidence import FactEvidence, FactEvidenceRole
from knowledge.provenance import Provenance, ProvenanceActor, ProvenanceStep
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult
from processing.extraction.candidate_fact import CandidateFact
from processing.knowledge_build.knowledge_build_result import KnowledgeBuildResult


class KnowledgeBuilder:

    def build(
        self,
        entity_resolution_result: EntityResolutionResult,
        candidate_facts: tuple[CandidateFact, ...],
    ) -> KnowledgeBuildResult:
        require(
            isinstance(entity_resolution_result, EntityResolutionResult),
            "entity_resolution_result must be an EntityResolutionResult",
        )
        require(
            isinstance(candidate_facts, tuple) and len(candidate_facts) >= 1,
            "candidate_facts must be a non-empty tuple",
        )

        entity_id: EntityId = entity_resolution_result.resolved_entity_id

        fact_by_candidate: dict[CandidateFactId, Fact] = {}
        evidence_by_candidate: dict[CandidateFactId, Evidence] = {}

        for cf in candidate_facts:
            fact_by_candidate[cf.candidate_fact_id] = _build_fact(entity_id, cf)
            evidence_by_candidate[cf.candidate_fact_id] = _build_evidence(entity_id, cf)

        fact_evidence_links = _build_fact_evidence_links(
            fact_by_candidate,
            evidence_by_candidate,
            candidate_facts,
        )

        provenance_records = _build_provenance_records(
            entity_id,
            fact_by_candidate,
            evidence_by_candidate,
            candidate_facts,
        )

        conflicts = _build_conflicts(
            entity_id,
            entity_resolution_result,
            fact_by_candidate,
        )

        return KnowledgeBuildResult.create(
            entity_id=entity_id,
            facts=tuple(fact_by_candidate.values()),
            evidence=tuple(evidence_by_candidate.values()),
            fact_evidence_links=fact_evidence_links,
            provenance_records=provenance_records,
            conflicts=conflicts,
        )


def _build_fact(entity_id: EntityId, cf: CandidateFact) -> Fact:
    return Fact.create(
        entity_id=entity_id,
        field_name=cf.fact_type,
        canonical_value=cf.normalized_value,
        display_value=cf.normalized_value,
        source_stage=cf.source_stage,  # ✅ مطلوب من Fact.create()
        confidence=cf.confidence,
    )


def _build_evidence(entity_id: EntityId, cf: CandidateFact) -> Evidence:
    return Evidence.create(
        source_id=cf.source_id,
        entity_id=entity_id,
        field_name=cf.fact_type,
        raw_value=cf.raw_value,
        extraction_method=cf.source_stage,
        confidence=cf.confidence,
        location={"span_ids": list(cf.span_ids)},
        metadata={"document_id": cf.document_id},
    )


def _build_fact_evidence_links(
    fact_by_candidate: dict[CandidateFactId, Fact],
    evidence_by_candidate: dict[CandidateFactId, Evidence],
    candidate_facts: tuple[CandidateFact, ...],
) -> tuple[FactEvidence, ...]:
    links: list[FactEvidence] = []

    for cf in candidate_facts:
        fact = fact_by_candidate.get(cf.candidate_fact_id)
        evidence = evidence_by_candidate.get(cf.candidate_fact_id)
        if fact is None or evidence is None:
            continue

        links.append(
            FactEvidence.create(
                fact_id=fact.fact_id,
                evidence_id=evidence.evidence_id,
                role=FactEvidenceRole.PRIMARY,
            )
        )

    return tuple(links)


def _build_provenance_records(
    entity_id: EntityId,
    fact_by_candidate: dict[CandidateFactId, Fact],
    evidence_by_candidate: dict[CandidateFactId, Evidence],
    candidate_facts: tuple[CandidateFact, ...],
) -> tuple[Provenance, ...]:
    records: list[Provenance] = []

    for cf in candidate_facts:
        fact = fact_by_candidate.get(cf.candidate_fact_id)
        evidence = evidence_by_candidate.get(cf.candidate_fact_id)
        if fact is None:
            continue

        records.append(
            Provenance.create(
                fact_id=fact.fact_id,
                entity_id=entity_id,
                decision_chain=[  # ✅ list وليس tuple
                    ProvenanceStep(
                        step_order=0,
                        action="extracted",
                        actor=_resolve_actor(cf.source_stage),
                        occurred_at=fact.created_at,
                        evidence_id=evidence.evidence_id if evidence else None,
                        note=f"raw_value={cf.raw_value!r} confidence={cf.confidence}",
                    ),
                ],
                summary=(
                    f"Fact '{cf.fact_type}' extracted from source "
                    f"'{cf.source_id}' with confidence {cf.confidence}"
                ),
            )
        )

    return tuple(records)


def _build_conflicts(
    entity_id: EntityId,
    resolution: EntityResolutionResult,
    fact_by_candidate: dict[CandidateFactId, Fact],
) -> tuple[Conflict, ...]:
    if not resolution.has_conflicts:
        return ()

    conflicts: list[Conflict] = []

    for field_name, competing_ids in resolution.conflict_details.items():
        fact_ids: list[str] = []  # ✅ list[str] كما يطلب Conflict.create()

        for cid in competing_ids:
            fact = fact_by_candidate.get(cid)
            if fact is None:
                continue
            fact_ids.append(fact.fact_id)

        if len(fact_ids) < 2:
            continue

        conflicts.append(
            Conflict.create(
                entity_id=entity_id,
                field_name=field_name,
                fact_ids=fact_ids,
            )
        )

    return tuple(conflicts)


def _resolve_actor(source_stage: str) -> str:
    mapping: dict[str, str] = {
        "ocr": ProvenanceActor.OCR,
        "mrz": ProvenanceActor.SYSTEM,
        "regex": ProvenanceActor.SYSTEM,
        "manual": ProvenanceActor.USER,
    }
    return mapping.get(source_stage.lower(), ProvenanceActor.SYSTEM)
