from __future__ import annotations

from pathlib import Path
from typing import Any

from core.types import ReviewCaseId
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
from ui.viewmodels.review_models import ReviewStatus as UIReviewStatus

FIELD_LABELS: dict[str, str] = {
    "given_names": "Given names / Vorname",
    "surname": "Surname / Familienname / Nachname",
    "date_of_birth": "Date of birth / Geburtsdatum",
    "place_of_birth": "Place of birth / Geburtsort",
    "nationality": "Nationality / Staatsangehörigkeit",
    "sex": "Sex / Geschlecht",
    "address": "Address / Anschrift",
    "passport_number": "Passport number / Passnummer",
    "issuing_authority": "Issuing authority / Ausstellende Behörde",
    "email": "Email",
    "phone_number": "Phone number / Telefonnummer",
    "employer": "Employer / Arbeitgeber",
    "employee": "Employee / Arbeitnehmer",
    "job_title": "Job title / Berufsbezeichnung",
    "start_date": "Start date / Beginn",
    "salary": "Salary / Gehalt",
    "working_hours": "Working hours / Arbeitszeit",
    "amount": "Amount / Betrag",
    "date": "Date / Datum",
    "other": "Other",
}

FIELD_OPTIONS: tuple[str, ...] = tuple(FIELD_LABELS.keys())

GERMAN_LABEL_MAP: dict[str, str] = {
    "vorname": "given_names",
    "vornamen": "given_names",
    "name": "surname",
    "familienname": "surname",
    "nachname": "surname",
    "geburtsdatum": "date_of_birth",
    "geburtsort": "place_of_birth",
    "geburtsland": "place_of_birth",
    "staatsangehörigkeit": "nationality",
    "nationalität": "nationality",
    "geschlecht": "sex",
    "anschrift": "address",
    "adresse": "address",
    "straße": "address",
    "strasse": "address",
    "passnummer": "passport_number",
    "reisepassnummer": "passport_number",
    "ausstellende behörde": "issuing_authority",
    "arbeitgeber": "employer",
    "arbeitnehmer": "employee",
    "mitarbeiter": "employee",
    "berufsbezeichnung": "job_title",
    "beginn": "start_date",
    "eintritt": "start_date",
    "gehalt": "salary",
    "vergütung": "salary",
    "arbeitszeit": "working_hours",
    "telefon": "phone_number",
    "telefonnummer": "phone_number",
    "betrag": "amount",
    "datum": "date",
}

LOW_VALUE_FACT_TYPES = {
    "review_candidate",
    "bic",
}

BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("90% - 100%", 0.90, 1.01),
    ("80% - 90%", 0.80, 0.90),
    ("70% - 80%", 0.70, 0.80),
    ("60% - 70%", 0.60, 0.70),
    ("50% - 60%", 0.50, 0.60),
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


def _guess_canonical_field(
    fact_type: str, raw_value: str, normalized_value: str
) -> str:
    candidates = [
        str(fact_type or "").strip().lower(),
        str(raw_value or "").strip().lower(),
        str(normalized_value or "").strip().lower(),
    ]

    for value in candidates:
        if value in FIELD_OPTIONS:
            return value

    for value in candidates:
        clean = value.replace(":", "").strip()
        if clean in GERMAN_LABEL_MAP:
            return GERMAN_LABEL_MAP[clean]

    return "other"


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
    value = case.normalized_value or case.raw_value or ""
    label = f"{case.fact_type} · {value}"
    return ReviewCaseSummary(
        case_id=str(case.review_case_id),
        label=label,
        status=_map_status(case.status),
    )


def _case_to_detail(case: ReviewCase) -> ReviewCaseDetail:
    edited_value = str(case.metadata.get("edited_value") or "")
    edited_field = str(case.metadata.get("edited_field") or "")
    value = edited_value or case.normalized_value or case.raw_value or ""
    canonical_field = edited_field or _guess_canonical_field(
        str(case.fact_type),
        str(case.raw_value),
        str(case.normalized_value),
    )

    return ReviewCaseDetail(
        case_id=str(case.review_case_id),
        document_reference=_resolve_document_reference(case),
        entity_name=str(case.entity_id),
        status=_map_status(case.status),
        suggestions=(
            Suggestion(
                field=canonical_field,
                value=value,
                status=_map_status(case.status),
            ),
        ),
        confidence=float(case.confidence),
        metadata=dict(case.metadata),
        fact_type=str(case.fact_type),
        raw_value=str(case.raw_value or ""),
        normalized_value=str(case.normalized_value or ""),
        canonical_field=canonical_field,
        field_options=FIELD_OPTIONS,
    )


class ReviewVM:

    def field_label(self, field_name: str) -> str:
        return FIELD_LABELS.get(field_name, field_name)

    def load_metrics(self) -> dict[str, int]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return {
                "pending": 0,
                "accepted": 0,
                "rejected": 0,
                "visible": 0,
                "hidden_for_llm": 0,
            }

        conn = _get_db().connection

        def count(where: str, params: tuple[Any, ...]) -> int:
            row = conn.execute(
                f"SELECT COUNT(*) AS c FROM review_cases WHERE {where}",
                params,
            ).fetchone()
            return int(row["c"]) if row else 0

        pending = count("entity_id = ? AND status = 'PENDING'", (entity_id,))
        accepted = count(
            "entity_id = ? AND status IN ('COMPLETED', 'ACCEPTED')",
            (entity_id,),
        )
        rejected = count(
            "entity_id = ? AND status IN ('CANCELLED', 'REJECTED')",
            (entity_id,),
        )
        visible = count(
            """
            entity_id = ?
            AND status = 'PENDING'
            AND confidence >= 0.5
            AND fact_type NOT IN ('review_candidate', 'bic')
            """,
            (entity_id,),
        )
        hidden_for_llm = count(
            """
            entity_id = ?
            AND status = 'PENDING'
            AND (
                confidence < 0.5
                OR fact_type IN ('review_candidate', 'bic')
            )
            """,
            (entity_id,),
        )

        return {
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "visible": visible,
            "hidden_for_llm": hidden_for_llm,
        }

    def load_bucketed_queue(
        self,
        limit_per_bucket: int = 20,
        include_low_value: bool = False,
        search: str = "",
        fact_type: str = "All",
    ) -> dict[str, tuple[ReviewCaseSummary, ...]]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return {label: () for label, _, _ in BUCKETS}

        conn = _get_db().connection
        repo = get_review_repo()
        result: dict[str, tuple[ReviewCaseSummary, ...]] = {}

        search_value = f"%{search.strip()}%" if search.strip() else ""
        excluded = tuple(LOW_VALUE_FACT_TYPES)

        for label, low, high in BUCKETS:
            params: list[Any] = [entity_id, low, high]
            clauses = [
                "entity_id = ?",
                "status = 'PENDING'",
                "confidence >= ?",
                "confidence < ?",
            ]

            if not include_low_value:
                placeholders = ",".join("?" for _ in excluded)
                clauses.append(f"fact_type NOT IN ({placeholders})")
                params.extend(excluded)

            if fact_type != "All":
                clauses.append("fact_type = ?")
                params.append(fact_type)

            if search_value:
                clauses.append(
                    "(raw_value LIKE ? OR normalized_value LIKE ? OR fact_type LIKE ?)"
                )
                params.extend([search_value, search_value, search_value])

            where = " AND ".join(clauses)

            rows = conn.execute(
                f"""
                SELECT review_case_id
                FROM review_cases
                WHERE {where}
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
                """,
                tuple(params + [limit_per_bucket]),
            ).fetchall()

            cases: list[ReviewCaseSummary] = []
            for row in rows:
                case = repo.get(ReviewCaseId(str(row["review_case_id"])))
                if case is not None:
                    cases.append(_case_to_summary(case))

            result[label] = tuple(cases)

        return result

    def load_fact_types(self) -> tuple[str, ...]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return ("All",)

        rows = (
            _get_db()
            .connection.execute(
                """
            SELECT DISTINCT fact_type
            FROM review_cases
            WHERE entity_id = ?
              AND status = 'PENDING'
              AND confidence >= 0.5
            ORDER BY fact_type
            """,
                (entity_id,),
            )
            .fetchall()
        )

        values = [str(row["fact_type"]) for row in rows]
        return tuple(["All"] + values)

    def load_queue(self) -> tuple[ReviewCaseSummary, ...]:
        bucketed = self.load_bucketed_queue(limit_per_bucket=20)
        merged: list[ReviewCaseSummary] = []
        for items in bucketed.values():
            merged.extend(items)
        return tuple(merged)

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
        edited_field: str | None = None,
    ) -> DecisionResult:
        try:
            repo = get_review_repo()
            case = repo.get(ReviewCaseId(case_id))
            if case is None:
                return DecisionResult(success=False, error="Case not found")

            field_name = (edited_field or "").strip() or _guess_canonical_field(
                str(case.fact_type),
                str(case.raw_value),
                str(case.normalized_value),
            )
            value = (edited_value or "").strip()

            if decision == DecisionType.EDIT:
                if not value:
                    return DecisionResult(success=False, error="Edited value is empty")
                updated = case.with_metadata("edited_value", value).with_metadata(
                    "edited_field",
                    field_name,
                )
                repo.save(updated)
                return DecisionResult(
                    success=True,
                    case_id=case_id,
                    decision=decision,
                    message="Edit saved",
                )

            if decision == DecisionType.REJECT:
                updated = case.cancel()
                repo.save(updated)
                self._reject_fact_from_case(case)
                return DecisionResult(
                    success=True,
                    case_id=case_id,
                    decision=decision,
                    message="Rejected",
                )

            if decision == DecisionType.ACCEPT:
                if not value:
                    value = str(case.metadata.get("edited_value") or "").strip()
                if not value:
                    value = case.normalized_value.strip() or case.raw_value.strip()

                if not value:
                    return DecisionResult(success=False, error="Value is empty")

                if field_name not in FIELD_OPTIONS:
                    field_name = "other"

                self._accept_fact_from_case(case, field_name, value, actor)

                updated = (
                    case.with_metadata("accepted_value", value)
                    .with_metadata("accepted_field", field_name)
                    .with_metadata("original_fact_type", str(case.fact_type))
                    .with_metadata("original_raw_value", str(case.raw_value))
                )

                updated = self._complete_case_safely(updated)
                repo.save(updated)

                return DecisionResult(
                    success=True,
                    case_id=case_id,
                    decision=decision,
                    message="Accepted",
                )

            return DecisionResult(success=False, error=f"Unknown decision: {decision}")

        except Exception as exc:
            return DecisionResult(success=False, error=str(exc))

    def decide(
        self,
        case_id: str,
        decision: DecisionType,
        actor: str = "reviewer",
        edited_value: str | None = None,
        edited_field: str | None = None,
    ) -> DecisionResult:
        return self.submit_decision(
            case_id, decision, actor, edited_value, edited_field
        )

    def _complete_case_safely(self, case: ReviewCase) -> ReviewCase:
        if case.status == ReviewStatus.IN_REVIEW:
            return case.complete()

        if case.status in (ReviewStatus.PENDING, ReviewStatus.ASSIGNED):
            return case.__class__(
                review_case_id=case.review_case_id,
                entity_id=case.entity_id,
                candidate_fact_id=case.candidate_fact_id,
                fact_type=case.fact_type,
                raw_value=case.raw_value,
                normalized_value=case.normalized_value,
                confidence=case.confidence,
                evidence_ids=case.evidence_ids,
                status=ReviewStatus.COMPLETED,
                priority=case.priority,
                created_at=case.created_at,
                assigned_to=case.assigned_to,
                metadata=dict(case.metadata),
            )

        return case

    def _fact_ids_from_case(self, case: ReviewCase) -> tuple[str, ...]:
        values = [
            str(case.metadata.get("fact_id") or ""),
            str(case.candidate_fact_id or ""),
        ]
        return tuple(v for v in values if v)

    def _accept_fact_from_case(
        self,
        case: ReviewCase,
        field_name: str,
        value: str,
        actor: str,
    ) -> None:
        fact_ids = self._fact_ids_from_case(case)
        if not fact_ids:
            return

        db = _get_db()
        conn = db.connection

        for fact_id in fact_ids:
            conn.execute(
                """
                UPDATE facts
                SET field_name = ?,
                    canonical_value = ?,
                    display_value = ?,
                    status = 'accepted',
                    accepted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                    accepted_by = ?
                WHERE fact_id = ?
                """,
                (field_name, value, value, actor, fact_id),
            )

        conn.commit()

    def _reject_fact_from_case(self, case: ReviewCase) -> None:
        fact_ids = self._fact_ids_from_case(case)
        if not fact_ids:
            return

        db = _get_db()
        conn = db.connection

        for fact_id in fact_ids:
            conn.execute(
                """
                UPDATE facts
                SET status = 'rejected',
                    accepted_at = NULL,
                    accepted_by = NULL
                WHERE fact_id = ?
                """,
                (fact_id,),
            )

        conn.commit()
