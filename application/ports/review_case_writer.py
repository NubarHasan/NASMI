from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.types import (
    CandidateFactId,
    ConfidenceScore,
    EntityId,
    EvidenceId,
)
from review.review_case import ReviewCase
from review.review_type import ReviewPriority


@runtime_checkable
class ReviewCaseWriter(Protocol):
    def open_case(
        self,
        entity_id: EntityId,
        candidate_fact_id: CandidateFactId,
        fact_type: str,
        raw_value: str,
        normalized_value: str,
        confidence: ConfidenceScore,
        evidence_ids: tuple[EvidenceId, ...],
        priority: ReviewPriority = ReviewPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> ReviewCase: ...
