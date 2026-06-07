from __future__ import annotations

import logging

from application.services.knowledge_service import KnowledgeApplicationService
from core.guards import require
from core.types import EntityId
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult
from processing.extraction.candidate_fact import CandidateFact
from processing.knowledge_build.knowledge_build_result import KnowledgeBuildResult
from processing.knowledge_build.knowledge_builder import KnowledgeBuilder

_logger = logging.getLogger(__name__)


class KnowledgeBuildService:

    def __init__(self, knowledge_service: KnowledgeApplicationService) -> None:
        self._knowledge_service = knowledge_service
        self._builder = KnowledgeBuilder()

    def process(
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
            "candidate_facts must be a non-empty tuple of CandidateFact",
        )

        entity_id: EntityId = entity_resolution_result.resolved_entity_id

        _logger.debug(
            "KnowledgeBuildService.process started | entity_id=%s facts=%d",
            entity_id,
            len(candidate_facts),
        )

        result: KnowledgeBuildResult = self._builder.build(
            entity_resolution_result=entity_resolution_result,
            candidate_facts=candidate_facts,
        )

        self._knowledge_service.persist_knowledge_build(
            facts=list(result.facts),
            evidence_list=list(result.evidence),
            fact_evidence_links=list(result.fact_evidence_links),
            provenance_list=list(result.provenance_records),
            conflicts=list(result.conflicts),
        )

        _logger.debug(
            "KnowledgeBuildService.process completed | entity_id=%s facts=%d evidence=%d conflicts=%d",
            entity_id,
            len(result.facts),
            len(result.evidence),
            len(result.conflicts),
        )

        return result
