from __future__ import annotations

import logging
from typing import Final

from application.ports.review_case_writer import ReviewCaseWriter
from application.services.knowledge_service import KnowledgeApplicationService
from core.guards import require
from core.identifiers import is_valid_entity_id
from core.types import CandidateFactId, EntityId
from knowledge.conflict import Conflict
from knowledge.fact import Fact, FactStatus
from processing.fact_acceptance.fact_acceptance_result import FactAcceptanceResult
from review.review_case import ReviewCase
from review.review_type import ReviewPriority

_log = logging.getLogger(__name__)

_AUTO_ACCEPT_THRESHOLD: Final[float] = 0.75
_SYSTEM_ACTOR: Final[str] = "system"


def _resolve_priority(confidence: float) -> ReviewPriority:
    if confidence < 0.40:
        return ReviewPriority.HIGH
    if confidence < 0.60:
        return ReviewPriority.NORMAL
    return ReviewPriority.LOW


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
            f
            for f in self._knowledge.list_facts_by_entity(entity_id)
            if f.status == FactStatus.PENDING
        )

        require(
            len(pending_facts) > 0,
            f"no PENDING facts found for entity [{entity_id}]",
        )

        accepted: list[Fact] = []
        review_cases: list[ReviewCase] = []
        conflicts: list[Conflict] = []
        rejected: list[Fact] = []

        for fact in pending_facts:
            if fact.confidence >= _AUTO_ACCEPT_THRESHOLD:
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
            else:
                evidence_ids = self._knowledge.list_evidence_ids(fact.fact_id)
                if not evidence_ids:
                    _log.warning(
                        "skipping review — no evidence for fact=%s field=%s",
                        fact.fact_id,
                        fact.field_name,
                    )
                    rejected.append(fact)
                    continue

                case = self._review.open_case(
                    entity_id=fact.entity_id,
                    candidate_fact_id=CandidateFactId(str(fact.fact_id)),
                    fact_type=fact.field_name,
                    raw_value=fact.display_value,
                    normalized_value=fact.display_value,
                    confidence=fact.confidence,
                    evidence_ids=evidence_ids,
                    priority=_resolve_priority(fact.confidence),
                )
                review_cases.append(case)

        return FactAcceptanceResult.create(
            entity_id=entity_id,
            accepted_facts=tuple(accepted),
            review_cases=tuple(review_cases),
            conflicts=tuple(conflicts),
            rejected_facts=tuple(rejected),
        )
