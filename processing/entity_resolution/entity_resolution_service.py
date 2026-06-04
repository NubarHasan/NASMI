from __future__ import annotations

import logging

from processing.candidate_fact import CandidateFact

from core.guards import require
from core.types import EntityId
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult
from processing.entity_resolution.entity_resolver import EntityResolver

_log = logging.getLogger(__name__)


class EntityResolutionService:

    def __init__(self, resolver: EntityResolver) -> None:
        require(
            isinstance(resolver, EntityResolver),
            "resolver must be an EntityResolver",
        )
        self._resolver = resolver

    def resolve(
        self,
        facts: list[CandidateFact],
        entity_id: EntityId | None = None,
    ) -> EntityResolutionResult:
        require(
            bool(facts),
            "facts cannot be empty",
        )

        _log.debug(
            "resolving %d candidate fact(s) — entity_id=%s",
            len(facts),
            entity_id or "<new>",
        )

        result = self._resolver.resolve(facts=facts, entity_id=entity_id)

        if result.has_conflicts:
            _log.warning(
                "resolved entity_id=%s with conflicts — conflict_fact_types=%s "
                "confidence=%.3f",
                result.resolved_entity_id,
                list(result.conflict_fact_types),
                result.resolution_confidence,
            )
        else:
            _log.info(
                "resolved entity_id=%s — facts=%d confidence=%.3f",
                result.resolved_entity_id,
                result.fact_count,
                result.resolution_confidence,
            )

        return result
