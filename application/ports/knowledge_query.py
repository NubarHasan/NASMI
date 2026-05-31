from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.types import EntityId
from knowledge.fact import Fact


@runtime_checkable
class KnowledgeQueryService(Protocol):
    """
    Read-only access to accepted knowledge facts.

    Implementations must:
        - Return only FactStatus.ACCEPTED facts.
        - Never mutate knowledge records.
        - Return an empty tuple when no facts exist for entity_id.
    """

    def list_accepted_facts(
        self,
        entity_id: EntityId,
    ) -> tuple[Fact, ...]: ...
