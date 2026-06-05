from __future__ import annotations

from application.services.review_service import ReviewApplicationService
from core.guards import require
from core.types import CandidateFactId, ConfidenceScore, EntityId, EvidenceId
from review.review_case import ReviewCase
from review.review_type import ReviewPriority


class ReviewCaseWriterAdapter:
    """
    Adapts ReviewApplicationService → ReviewCaseWriter Port.

    FactAcceptanceService يستدعي open_case(**fields).
    ReviewApplicationService يتوقع open_case(case: ReviewCase).
    هذا الـ Adapter يبني الـ ReviewCase ويفوّض للـ Application Service.
    """

    def __init__(self, service: ReviewApplicationService) -> None:
        require(
            isinstance(service, ReviewApplicationService),
            "service must be a ReviewApplicationService",
        )
        self._service = service

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
    ) -> ReviewCase:
        case = ReviewCase.create(
            entity_id=entity_id,
            candidate_fact_id=candidate_fact_id,
            fact_type=fact_type,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=confidence,
            evidence_ids=evidence_ids,
            priority=priority,
        )
        return self._service.open_case(case)
