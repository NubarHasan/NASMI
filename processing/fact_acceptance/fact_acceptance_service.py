from __future__ import annotations

import json
import logging
from typing import Any, Final

from application.ports.review_case_writer import ReviewCaseWriter
from application.services.knowledge_service import KnowledgeApplicationService
from core.guards import require
from core.identifiers import generate_candidate_fact_id, is_valid_entity_id
from core.types import EntityId
from knowledge.conflict import Conflict
from knowledge.fact import Fact, FactStatus
from processing.fact_acceptance.fact_acceptance_result import FactAcceptanceResult
from review.review_case import ReviewCase
from review.review_type import ReviewPriority

_log = logging.getLogger(__name__)

_MRZ_AUTO_ACCEPT_THRESHOLD: Final[float] = 0.90
_SYSTEM_ACTOR: Final[str] = "system"

_NEVER_AUTO_ACCEPT_FIELDS: frozenset[str] = frozenset(
    {
        "document_label",
        "review_candidate",
        "possible_location",
        "possible_date",
        "document_keyword",
        "mrz_confidence",
        "mrz_status",
        "mrz_check_passed",
    }
)

_OCR_REVIEW_FIELDS: frozenset[str] = frozenset(
    {
        "passport_number",
        "document_number",
        "surname",
        "given_names",
        "nationality",
        "date_of_birth",
        "date_of_expiry",
        "date_of_issue",
        "place_of_birth",
        "issuing_authority",
        "personal_number",
        "sex",
        "eye_color",
        "height",
    }
)


def _resolve_priority(confidence: float) -> ReviewPriority:
    if confidence < 0.40:
        return ReviewPriority.HIGH
    if confidence < 0.60:
        return ReviewPriority.NORMAL
    return ReviewPriority.LOW


def _safe_json_loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if not isinstance(value, str) or not value.strip():
        return {}

    try:
        loaded = json.loads(value)
    except Exception:
        return {}

    return loaded if isinstance(loaded, dict) else {}


class FactAcceptanceService:

    def __init__(
        self,
        knowledge_service: KnowledgeApplicationService,
        review_writer: ReviewCaseWriter,
    ) -> None:
        require(
            isinstance(knowledge_service, KnowledgeApplicationService),
            "knowledge_service must be a KnowledgeApplicationService",
        )
        require(
            isinstance(review_writer, ReviewCaseWriter),
            "review_writer must implement ReviewCaseWriter",
        )
        self._knowledge = knowledge_service
        self._review = review_writer

    def process(self, entity_id: EntityId) -> FactAcceptanceResult:
        require(is_valid_entity_id(entity_id), "invalid entity_id")

        pending_facts = tuple(
            fact
            for fact in self._knowledge.list_facts_by_entity(entity_id)
            if fact.status == FactStatus.PENDING
        )

        if not pending_facts:
            _log.info(
                "no PENDING facts found for entity [%s], skipping acceptance", entity_id
            )
            return FactAcceptanceResult.create(
                entity_id=entity_id,
                accepted_facts=(),
                review_cases=(),
                conflicts=(),
                rejected_facts=(),
            )

        accepted: list[Fact] = []
        review_cases: list[ReviewCase] = []
        conflicts: list[Conflict] = []
        rejected: list[Fact] = []

        for fact in pending_facts:
            evidence_ids = tuple(self._knowledge.list_evidence_ids(fact.fact_id))
            metadata = self._metadata_for_fact(fact, evidence_ids)

            if self._should_auto_accept(fact, metadata):
                outcome = self._knowledge.accept_fact(
                    fact_id=fact.fact_id,
                    accepted_by=_SYSTEM_ACTOR,
                )

                if isinstance(outcome, Fact):
                    if outcome.status == FactStatus.ACCEPTED:
                        accepted.append(outcome)
                    else:
                        rejected.append(outcome)
                elif isinstance(outcome, Conflict):
                    conflicts.append(outcome)

                continue

            if not evidence_ids:
                _log.warning(
                    "skipping review — no evidence for fact=%s field=%s",
                    fact.fact_id,
                    fact.field_name,
                )
                rejected.append(fact)
                continue

            case_metadata = {
                "fact_id": str(fact.fact_id),
                "field_name": fact.field_name,
                "original_value": fact.display_value,
                "canonical_value": fact.canonical_value,
                "confidence": fact.confidence,
                "review_editable": True,
                "auto_accept": False,
                "source": metadata.get("source", "unknown"),
                "evidence_metadata": metadata,
            }

            case = self._review.open_case(
                entity_id=fact.entity_id,
                candidate_fact_id=generate_candidate_fact_id(),
                fact_type=fact.field_name,
                raw_value=fact.display_value,
                normalized_value=fact.display_value,
                confidence=fact.confidence,
                evidence_ids=evidence_ids,
                priority=_resolve_priority(fact.confidence),
                metadata=case_metadata,
            )
            review_cases.append(case)

        return FactAcceptanceResult.create(
            entity_id=entity_id,
            accepted_facts=tuple(accepted),
            review_cases=tuple(review_cases),
            conflicts=tuple(conflicts),
            rejected_facts=tuple(rejected),
        )

    def _should_auto_accept(self, fact: Fact, metadata: dict[str, Any]) -> bool:
        if fact.field_name in _NEVER_AUTO_ACCEPT_FIELDS:
            return False

        if metadata.get("auto_accept") is False:
            return False

        if metadata.get("role") == "document_label":
            return False

        if metadata.get("is_person_fact") is False:
            return False

        source = str(metadata.get("source", "")).lower()
        mrz_check_passed = metadata.get("mrz_check_passed")

        if source == "mrz":
            return (
                bool(mrz_check_passed) and fact.confidence >= _MRZ_AUTO_ACCEPT_THRESHOLD
            )

        if fact.field_name in _OCR_REVIEW_FIELDS:
            return False

        return False

    def _metadata_for_fact(
        self,
        fact: Fact,
        evidence_ids: tuple,
    ) -> dict[str, Any]:
        if not evidence_ids:
            return {}

        try:
            rows = self._knowledge.list_evidence_for_fact(fact.fact_id)
            if rows:
                ev = rows[0]
                metadata = getattr(ev, "metadata", {}) or {}
                return _safe_json_loads(metadata)
        except Exception:
            return {}

        return {}
