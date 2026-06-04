from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import is_valid_entity_id
from core.time import utcnow
from core.types import EntityId
from knowledge.conflict import Conflict
from knowledge.fact import Fact
from review.review_case import ReviewCase


@dataclass(frozen=True)
class FactAcceptanceResult:
    entity_id: EntityId
    accepted_facts: tuple[Fact, ...]
    review_cases: tuple[ReviewCase, ...]
    conflicts: tuple[Conflict, ...]
    rejected_facts: tuple[Fact, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        require(
            is_valid_entity_id(self.entity_id), f"invalid entity_id: {self.entity_id!r}"
        )
        require(
            isinstance(self.accepted_facts, tuple), "accepted_facts must be a tuple"
        )
        require(
            all(isinstance(f, Fact) for f in self.accepted_facts),
            "all items in accepted_facts must be Fact instances",
        )
        require(isinstance(self.review_cases, tuple), "review_cases must be a tuple")
        require(
            all(isinstance(c, ReviewCase) for c in self.review_cases),
            "all items in review_cases must be ReviewCase instances",
        )
        require(isinstance(self.conflicts, tuple), "conflicts must be a tuple")
        require(
            all(isinstance(c, Conflict) for c in self.conflicts),
            "all items in conflicts must be Conflict instances",
        )
        require(
            isinstance(self.rejected_facts, tuple), "rejected_facts must be a tuple"
        )
        require(
            all(isinstance(f, Fact) for f in self.rejected_facts),
            "all items in rejected_facts must be Fact instances",
        )
        require(isinstance(self.created_at, datetime), "created_at must be a datetime")

    @classmethod
    def create(
        cls,
        entity_id: EntityId,
        accepted_facts: tuple[Fact, ...],
        review_cases: tuple[ReviewCase, ...],
        conflicts: tuple[Conflict, ...],
        rejected_facts: tuple[Fact, ...],
    ) -> FactAcceptanceResult:
        return cls(
            entity_id=entity_id,
            accepted_facts=accepted_facts,
            review_cases=review_cases,
            conflicts=conflicts,
            rejected_facts=rejected_facts,
            created_at=utcnow(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": str(self.entity_id),
            "accepted_count": len(self.accepted_facts),
            "review_required_count": len(self.review_cases),
            "conflict_count": len(self.conflicts),
            "rejected_count": len(self.rejected_facts),
            "accepted_fact_ids": [str(f.fact_id) for f in self.accepted_facts],
            "review_case_ids": [str(c.review_case_id) for c in self.review_cases],
            "conflict_ids": [str(c.conflict_id) for c in self.conflicts],
            "rejected_fact_ids": [str(f.fact_id) for f in self.rejected_facts],
            "created_at": self.created_at.isoformat(),
        }
