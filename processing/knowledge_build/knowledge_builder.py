from __future__ import annotations

import re

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

_EVIDENCE_ONLY_TYPES: frozenset[str] = frozenset(
    {
        "document_label",
    }
)

_REVIEW_ONLY_TYPES: frozenset[str] = frozenset(
    {
        "review_candidate",
    }
)

_DATE_TYPES: frozenset[str] = frozenset(
    {
        "date",
        "date_value",
        "birth_date",
        "date_of_birth",
        "issue_date",
        "expiry_date",
        "expiration_date",
        "valid_until",
    }
)

_DATE_OF_BIRTH_HINTS: tuple[str, ...] = (
    "date of birth",
    "birth date",
    "geburtsdatum",
    "geboren",
    "born",
    "dob",
    "date naissance",
    "date de naissance",
    "تاريخ الميلاد",
)

_ISSUE_DATE_HINTS: tuple[str, ...] = (
    "issue date",
    "date of issue",
    "issued",
    "ausstellungsdatum",
    "ausgestellt",
    "date delivrance",
    "date de délivrance",
    "تاريخ الإصدار",
)

_EXPIRY_DATE_HINTS: tuple[str, ...] = (
    "expiry date",
    "expiration date",
    "expires",
    "valid until",
    "gültig bis",
    "ablaufdatum",
    "date expiration",
    "date d'expiration",
    "تاريخ الانتهاء",
)

_ENROLLMENT_DATE_HINTS: tuple[str, ...] = (
    "enrollment date",
    "registration date",
    "start date",
    "course start",
    "beginn",
    "anmeldung",
    "تاريخ التسجيل",
)


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
            evidence_by_candidate[cf.candidate_fact_id] = _build_evidence(entity_id, cf)

            if _should_build_fact(cf):
                fact_by_candidate[cf.candidate_fact_id] = _build_fact(entity_id, cf)

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


def _should_build_fact(cf: CandidateFact) -> bool:
    if cf.fact_type in _EVIDENCE_ONLY_TYPES:
        return False

    if cf.fact_type in _REVIEW_ONLY_TYPES:
        return False

    if cf.metadata.get("role") == "document_label":
        return False

    if cf.metadata.get("is_person_fact") is False:
        return False

    if cf.metadata.get("store_as_knowledge_evidence") is True:
        return False

    return not _looks_like_label_value(cf.normalized_value)


def _build_fact(entity_id: EntityId, cf: CandidateFact) -> Fact:
    field_name = _resolve_field_name(cf)

    return Fact.create(
        entity_id=entity_id,
        field_name=field_name,
        canonical_value=cf.normalized_value,
        display_value=cf.normalized_value,
        source_stage=cf.source_stage,
        confidence=cf.confidence,
    )


def _build_evidence(entity_id: EntityId, cf: CandidateFact) -> Evidence:
    metadata = dict(cf.metadata)
    metadata["document_id"] = str(cf.document_id)
    metadata["candidate_fact_id"] = str(cf.candidate_fact_id)
    metadata["fact_type"] = cf.fact_type
    metadata["resolved_field_name"] = _resolve_field_name(cf)

    return Evidence.create(
        source_id=cf.source_id,
        entity_id=entity_id,
        field_name=_resolve_field_name(cf),
        raw_value=cf.raw_value,
        extraction_method=cf.source_stage,
        confidence=cf.confidence,
        location={"span_ids": [str(s) for s in cf.span_ids]},
        metadata=metadata,
    )


def _resolve_field_name(cf: CandidateFact) -> str:
    target_field = cf.metadata.get("target_field")
    field_name = str(target_field) if target_field else str(cf.fact_type)

    if _is_date_candidate(cf, field_name):
        return _classify_date_field(cf, field_name)

    if field_name == "phone_number" and _looks_like_date(cf.normalized_value):
        return "date_of_birth"

    return field_name


def _is_date_candidate(cf: CandidateFact, field_name: str) -> bool:
    lowered_field = field_name.strip().lower()
    lowered_type = str(cf.fact_type).strip().lower()

    if lowered_field in _DATE_TYPES:
        return True

    if lowered_type in _DATE_TYPES:
        return True

    return bool(_looks_like_date(cf.normalized_value))


def _classify_date_field(cf: CandidateFact, fallback: str) -> str:
    context = _candidate_context_text(cf)

    if _contains_any(context, _DATE_OF_BIRTH_HINTS):
        return "date_of_birth"

    if _contains_any(context, _ISSUE_DATE_HINTS):
        return "issue_date"

    if _contains_any(context, _EXPIRY_DATE_HINTS):
        return "expiry_date"

    if _contains_any(context, _ENROLLMENT_DATE_HINTS):
        return "enrollment_date"

    if str(cf.metadata.get("target_field") or "").strip().lower() in {
        "date_of_birth",
        "issue_date",
        "expiry_date",
        "enrollment_date",
    }:
        return str(cf.metadata["target_field"]).strip().lower()

    if fallback.strip().lower() in {
        "birth_date",
        "date_of_birth",
    }:
        return "date_of_birth"

    if fallback.strip().lower() in {
        "expiration_date",
        "valid_until",
    }:
        return "expiry_date"

    return "date"


def _candidate_context_text(cf: CandidateFact) -> str:
    parts: list[str] = [
        str(cf.fact_type),
        str(cf.raw_value),
        str(cf.normalized_value),
        str(cf.source_stage),
    ]

    for key in (
        "target_field",
        "label",
        "nearby_label",
        "context",
        "line_text",
        "block_text",
        "page_text",
        "left_text",
        "right_text",
        "previous_text",
        "next_text",
        "source_label",
    ):
        value = cf.metadata.get(key)
        if value is not None:
            parts.append(str(value))

    return " ".join(parts).strip().lower()


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def _looks_like_date(value: str) -> bool:
    text = str(value).strip()
    patterns = (
        r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$",
        r"^\d{4}[./-]\d{1,2}[./-]\d{1,2}$",
        r"^\d{6}$",
        r"^\d{8}$",
    )
    return any(re.match(pattern, text) for pattern in patterns)


def _looks_like_label_value(value: str) -> bool:
    text = " ".join(str(value).strip().lower().split())

    if not text:
        return True

    labels = {
        "surname",
        "given names",
        "name",
        "date of birth",
        "birth date",
        "place of birth",
        "nationality",
        "sex",
        "address",
        "residence",
        "phone",
        "telephone",
        "telefon",
        "email",
        "prénoms",
        "/ prénoms",
        "religious name or pseudonym",
        "/ religious name or pseudonym /",
        "residence./ do",
    }

    if text in labels:
        return True

    return bool(len(text) <= 2 and not text.isdigit())


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
                decision_chain=[
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
                    f"Fact '{fact.field_name}' extracted from source "
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
        fact_ids: list[str] = []

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
    lowered = source_stage.lower()
    if "ocr" in lowered:
        return ProvenanceActor.OCR
    if "mrz" in lowered:
        return ProvenanceActor.SYSTEM
    if "regex" in lowered:
        return ProvenanceActor.SYSTEM
    if "manual" in lowered:
        return ProvenanceActor.USER
    return ProvenanceActor.SYSTEM
