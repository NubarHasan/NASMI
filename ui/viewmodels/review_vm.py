from __future__ import annotations

from ui.viewmodels.review_models import (
    Conflict,
    DecisionResult,
    DecisionType,
    Evidence,
    ReviewCaseDetail,
    ReviewCaseSummary,
    ReviewStatus,
    Suggestion,
)

_MOCK_QUEUE: tuple[ReviewCaseSummary, ...] = (
    ReviewCaseSummary(
        "case-001", "Nubar Hasan · Residence Permit", ReviewStatus.PENDING
    ),
    ReviewCaseSummary(
        "case-002", "Nubar Hasan · Employment Contract", ReviewStatus.PENDING
    ),
    ReviewCaseSummary(
        "case-003", "Nubar Hasan · Bank Statement Q1", ReviewStatus.ACCEPTED
    ),
)

_MOCK_CASES: dict[str, ReviewCaseDetail] = {
    "case-001": ReviewCaseDetail(
        case_id="case-001",
        document_reference="doc-002",
        entity_name="Nubar Hasan",
        status=ReviewStatus.PENDING,
        suggestions=(
            Suggestion("permit_number", "RP-2025-009821", ReviewStatus.ACCEPTED),
            Suggestion("valid_until", "2027-11-19", ReviewStatus.PENDING),
            Suggestion(
                "issuing_authority", "Immigration Authority", ReviewStatus.PENDING
            ),
        ),
        conflicts=(
            Conflict(
                conflict_id="conf-001",
                field="valid_until",
                value_a="2027-11-19",
                value_b="2027-12-01",
                evidence=(
                    Evidence(
                        "Residence Permit Scan p.1", "Valid Until: 2027-11-19", 1, 0.93
                    ),
                    Evidence(
                        "Immigration Registry Export",
                        "Expiry Date: 2027-12-01",
                        None,
                        0.85,
                    ),
                ),
            ),
        ),
    ),
    "case-002": ReviewCaseDetail(
        case_id="case-002",
        document_reference="doc-003",
        entity_name="Nubar Hasan",
        status=ReviewStatus.PENDING,
        suggestions=(
            Suggestion("employer", "TechCorp GmbH", ReviewStatus.PENDING),
            Suggestion("position", "Software Engineer", ReviewStatus.PENDING),
            Suggestion("start_date", "2026-02-01", ReviewStatus.ACCEPTED),
        ),
        conflicts=(),
    ),
}


class ReviewVM:
    def load_queue(self) -> tuple[ReviewCaseSummary, ...]:
        return _MOCK_QUEUE

    def refresh_queue(self) -> tuple[ReviewCaseSummary, ...]:
        return self.load_queue()

    def load_case_detail(self, case_id: str) -> ReviewCaseDetail | None:
        return _MOCK_CASES.get(case_id)

    def submit_decision(self, case_id: str, decision: DecisionType) -> DecisionResult:
        return DecisionResult(
            case_id=case_id,
            decision=decision,
            success=True,
        )
