from __future__ import annotations

from pathlib import Path

from core.types import EntityId, ReviewCaseId
from review.review_case import ReviewCase
from review.review_type import ReviewStatus
from ui.services.api_client import _get_db, get_review_repo
from ui.viewmodels.review_models import (
    DecisionResult,
    DecisionType,
    ReviewCaseDetail,
    ReviewCaseSummary,
    Suggestion,
)
from ui.viewmodels.review_models import (
    ReviewStatus as UIReviewStatus,
)


def _active_entity_id() -> str | None:
    try:
        from ui.state import session_manager as sm
        from ui.state.session_keys import SessionKeys

        val = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
        return str(val) if val is not None else None
    except Exception:
        return None


def _map_status(domain_status: ReviewStatus) -> UIReviewStatus:
    mapping: dict[ReviewStatus, UIReviewStatus] = {
        ReviewStatus.PENDING: UIReviewStatus.PENDING,
        ReviewStatus.ASSIGNED: UIReviewStatus.PENDING,
        ReviewStatus.IN_REVIEW: UIReviewStatus.PENDING,
        ReviewStatus.COMPLETED: UIReviewStatus.ACCEPTED,
        ReviewStatus.CANCELLED: UIReviewStatus.REJECTED,
    }
    return mapping.get(domain_status, UIReviewStatus.PENDING)


def _resolve_document_reference(case: ReviewCase) -> str:
    try:
        db = _get_db()
        conn = db.connection

        if not case.evidence_ids:
            return ""

        evidence_id = str(case.evidence_ids[0])
        ev_row = conn.execute(
            "SELECT source_id FROM evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()

        if not ev_row:
            return ""

        source_id = ev_row["source_id"]
        src_row = conn.execute(
            "SELECT document_id FROM sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()

        if not src_row or not src_row["document_id"]:
            return ""

        document_id = src_row["document_id"]
        doc_row = conn.execute(
            "SELECT file_path FROM documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()

        if not doc_row:
            return ""

        return Path(doc_row["file_path"]).name

    except Exception:
        return ""


def _case_to_summary(case: ReviewCase) -> ReviewCaseSummary:
    label = str(case.fact_type)
    if case.raw_value:
        label += f" · {case.raw_value}"
    return ReviewCaseSummary(
        case_id=str(case.review_case_id),
        label=label,
        status=_map_status(case.status),
    )


def _case_to_detail(case: ReviewCase) -> ReviewCaseDetail:
    return ReviewCaseDetail(
        case_id=str(case.review_case_id),
        document_reference=_resolve_document_reference(case),
        entity_name=str(case.entity_id),
        status=_map_status(case.status),
        suggestions=(
            Suggestion(
                field=str(case.fact_type),
                value=case.normalized_value or case.raw_value or "",
                status=_map_status(case.status),
            ),
        ),
        confidence=case.confidence,
        metadata=case.metadata,
    )


class ReviewVM:

    def load_queue(self) -> tuple[ReviewCaseSummary, ...]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return ()
        try:
            cases = get_review_repo().list_by_entity(EntityId(entity_id))
            return tuple(_case_to_summary(c) for c in cases)
        except Exception:
            return ()

    def load_cases(self) -> tuple[ReviewCaseSummary, ...]:
        return self.load_queue()

    def load_case_detail(self, case_id: str) -> ReviewCaseDetail | None:
        try:
            case = get_review_repo().get(ReviewCaseId(case_id))
            return _case_to_detail(case) if case else None
        except Exception:
            return None

    def load_case(self, case_id: str) -> ReviewCaseDetail | None:
        return self.load_case_detail(case_id)

    def submit_decision(
        self,
        case_id: str,
        decision: DecisionType,
        actor: str = "reviewer",
        edited_value: str | None = None,
    ) -> DecisionResult:
        try:
            repo = get_review_repo()
            case = repo.get(ReviewCaseId(case_id))
            if case is None:
                return DecisionResult(success=False, error="Case not found")

            if decision == DecisionType.ACCEPT:
                updated = (
                    case.complete() if case.status == ReviewStatus.IN_REVIEW else case
                )
            elif decision == DecisionType.REJECT:
                updated = case.cancel()
            elif decision == DecisionType.EDIT:
                updated = case.with_metadata("edited_value", edited_value or "")
            else:
                return DecisionResult(
                    success=False, error=f"Unknown decision: {decision}"
                )

            repo.save(updated)
            return DecisionResult(success=True)

        except Exception as exc:
            return DecisionResult(success=False, error=str(exc))

    def decide(
        self,
        case_id: str,
        decision: DecisionType,
        actor: str = "reviewer",
        edited_value: str | None = None,
    ) -> DecisionResult:
        return self.submit_decision(case_id, decision, actor, edited_value)
