from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from core.identifiers import generate_entity_id, generate_fact_id, generate_id
from core.time import utcnow_iso
from core.types import ReviewCaseId
from review.review_case import ReviewCase
from review.review_type import ReviewStatus
from ui.services.api_client import _get_db, get_review_repo
from ui.viewmodels.review_models import (
    DecisionResult,
    DecisionType,
    OwnerSelection,
    OwnerTarget,
    ReviewCaseDetail,
    ReviewCaseSummary,
    Suggestion,
)
from ui.viewmodels.review_models import ReviewStatus as UIReviewStatus

FIELD_LABELS: dict[str, str] = {
    "other": "Other / Sonstiges",
    "full_name": "Full name / Vollständiger Name",
    "given_names": "Given names / Vorname(n)",
    "first_name": "First name / Vorname",
    "middle_name": "Middle name / Zweitname",
    "surname": "Surname / Familienname / Nachname",
    "birth_name": "Birth name / Geburtsname",
    "preferred_name": "Preferred name / Rufname",
    "title": "Title / Titel",
    "academic_title": "Academic title / Akademischer Titel",
    "date_of_birth": "Date of birth / Geburtsdatum",
    "place_of_birth": "Place of birth / Geburtsort",
    "country_of_birth": "Country of birth / Geburtsland",
    "nationality": "Nationality / Staatsangehörigkeit",
    "second_nationality": "Second nationality / Zweite Staatsangehörigkeit",
    "sex": "Sex / Geschlecht",
    "gender": "Gender / Geschlecht",
    "marital_status": "Marital status / Familienstand",
    "religion": "Religion / Religionszugehörigkeit",
    "language": "Language / Sprache",
    "primary_language": "Primary language / Hauptsprache",
    "address": "Address / Anschrift",
    "address_full": "Full address / Vollständige Anschrift",
    "street": "Street / Straße",
    "house_number": "House number / Hausnummer",
    "address_extra": "Address extra / Adresszusatz",
    "postal_code": "Postal code / Postleitzahl",
    "city": "City / Stadt",
    "state": "State / Bundesland",
    "country": "Country / Land",
    "current_address": "Current address / Aktuelle Anschrift",
    "previous_address": "Previous address / Frühere Anschrift",
    "registered_address": "Registered address / Meldeadresse",
    "move_in_date": "Move-in date / Einzugsdatum",
    "move_out_date": "Move-out date / Auszugsdatum",
    "email": "Email / E-Mail",
    "private_email": "Private email / Private E-Mail",
    "university_email": "University email / Hochschul-E-Mail",
    "work_email": "Work email / Arbeits-E-Mail",
    "phone_number": "Phone number / Telefonnummer",
    "mobile_number": "Mobile number / Mobilnummer",
    "landline_number": "Landline number / Festnetznummer",
    "emergency_contact_name": "Emergency contact name / Notfallkontakt Name",
    "emergency_contact_phone": "Emergency contact phone / Notfallkontakt Telefon",
    "emergency_contact_relationship": "Emergency contact relationship / Beziehung Notfallkontakt",
    "passport_number": "Passport number / Passnummer",
    "passport_issue_date": "Passport issue date / Ausstellungsdatum Pass",
    "passport_expiry_date": "Passport expiry date / Ablaufdatum Pass",
    "passport_issuing_country": "Passport issuing country / Ausstellungsland Pass",
    "passport_issuing_authority": "Passport issuing authority / Ausstellende Behörde Pass",
    "national_id_number": "National ID number / Personalausweisnummer",
    "id_card_number": "ID card number / Ausweisnummer",
    "id_issue_date": "ID issue date / Ausstellungsdatum Ausweis",
    "id_expiry_date": "ID expiry date / Ablaufdatum Ausweis",
    "document_number": "Document number / Dokumentnummer",
    "document_type": "Document type / Dokumenttyp",
    "issuing_authority": "Issuing authority / Ausstellende Behörde",
    "issue_date": "Issue date / Ausstellungsdatum",
    "expiry_date": "Expiry date / Ablaufdatum",
    "valid_from": "Valid from / Gültig ab",
    "valid_until": "Valid until / Gültig bis",
    "mrz_line": "MRZ line / Maschinenlesbare Zone",
    "reference_number": "Reference number / Referenznummer",
    "case_number": "Case number / Aktenzeichen",
    "file_number": "File number / Vorgangsnummer",
    "visa_type": "Visa type / Visumtyp",
    "visa_number": "Visa number / Visumnummer",
    "visa_issue_date": "Visa issue date / Ausstellungsdatum Visum",
    "visa_expiry_date": "Visa expiry date / Ablaufdatum Visum",
    "visa_valid_from": "Visa valid from / Visum gültig ab",
    "visa_valid_until": "Visa valid until / Visum gültig bis",
    "residence_permit_number": "Residence permit number / Aufenthaltstitelnummer",
    "residence_title": "Residence title / Aufenthaltstitel",
    "residence_permit_type": "Residence permit type / Art des Aufenthaltstitels",
    "residence_permit_expiry": "Residence permit expiry / Ablauf Aufenthaltstitel",
    "immigration_authority": "Immigration authority / Ausländerbehörde",
    "entry_date": "Entry date / Einreisedatum",
    "entry_country": "Entry country / Einreiseland",
    "work_permit": "Work permit / Arbeitserlaubnis",
    "work_permit_valid_until": "Work permit valid until / Arbeitserlaubnis gültig bis",
    "university_name": "University name / Hochschule",
    "university": "University / Universität",
    "faculty": "Faculty / Fakultät",
    "department": "Department / Fachbereich",
    "campus": "Campus / Campus",
    "student_id": "Student ID / Studierenden-ID",
    "matriculation_number": "Matriculation number / Matrikelnummer",
    "applicant_number": "Applicant number / Bewerbernummer",
    "study_program": "Study program / Studiengang",
    "degree": "Degree / Abschluss",
    "semester": "Semester / Semester",
    "subject": "Subject / Fach",
    "major": "Major / Hauptfach",
    "minor": "Minor / Nebenfach",
    "enrollment_date": "Enrollment date / Immatrikulationsdatum",
    "exmatriculation_date": "Exmatriculation date / Exmatrikulationsdatum",
    "standard_period": "Standard period of study / Regelstudienzeit",
    "student_status": "Student status / Studierendenstatus",
    "exam_number": "Exam number / Prüfungsnummer",
    "grade": "Grade / Note",
    "ects": "ECTS credits / ECTS-Punkte",
    "health_insurance_provider": "Health insurance provider / Krankenversicherung",
    "health_insurance_number": "Health insurance number / Krankenversichertennummer",
    "insurance_number": "Insurance number / Versicherungsnummer",
    "policy_number": "Policy number / Policennummer",
    "insurance_start_date": "Insurance start date / Versicherungsbeginn",
    "insurance_end_date": "Insurance end date / Versicherungsende",
    "social_security_number": "Social security number / Sozialversicherungsnummer",
    "pension_insurance_number": "Pension insurance number / Rentenversicherungsnummer",
    "bank_name": "Bank name / Bankname",
    "account_holder": "Account holder / Kontoinhaber",
    "iban": "IBAN",
    "bic": "BIC",
    "account_number": "Account number / Kontonummer",
    "bank_code": "Bank code / Bankleitzahl",
    "tax_id": "Tax ID / Steuer-ID",
    "steuer_id": "Steuer-ID",
    "tax_number": "Tax number / Steuernummer",
    "vat_id": "VAT ID / Umsatzsteuer-ID",
    "amount": "Amount / Betrag",
    "currency": "Currency / Währung",
    "payment_reference": "Payment reference / Verwendungszweck",
    "invoice_number": "Invoice number / Rechnungsnummer",
    "customer_number": "Customer number / Kundennummer",
    "contract_number": "Contract number / Vertragsnummer",
    "employer": "Employer / Arbeitgeber",
    "employer_name": "Employer name / Arbeitgebername",
    "employee": "Employee / Arbeitnehmer",
    "employee_id": "Employee ID / Personalnummer",
    "job_title": "Job title / Berufsbezeichnung",
    "position": "Position / Position",
    "department_work": "Work department / Abteilung",
    "employment_type": "Employment type / Beschäftigungsart",
    "contract_start_date": "Contract start date / Vertragsbeginn",
    "contract_end_date": "Contract end date / Vertragsende",
    "start_date": "Start date / Beginn",
    "end_date": "End date / Ende",
    "probation_end_date": "Probation end date / Ende Probezeit",
    "salary": "Salary / Gehalt",
    "gross_salary": "Gross salary / Bruttogehalt",
    "net_salary": "Net salary / Nettogehalt",
    "hourly_wage": "Hourly wage / Stundenlohn",
    "working_hours": "Working hours / Arbeitszeit",
    "weekly_hours": "Weekly hours / Wochenstunden",
    "vacation_days": "Vacation days / Urlaubstage",
    "landlord_name": "Landlord name / Vermieter",
    "tenant_name": "Tenant name / Mieter",
    "rental_address": "Rental address / Mietadresse",
    "rent_amount": "Rent amount / Miete",
    "cold_rent": "Cold rent / Kaltmiete",
    "warm_rent": "Warm rent / Warmmiete",
    "deposit_amount": "Deposit amount / Kaution",
    "rental_contract_start_date": "Rental contract start date / Mietbeginn",
    "rental_contract_end_date": "Rental contract end date / Mietende",
    "room_number": "Room number / Zimmernummer",
    "apartment_number": "Apartment number / Wohnungsnummer",
    "date": "Date / Datum",
    "birth_date": "Birth date / Geburtsdatum",
    "deadline": "Deadline / Frist",
    "appointment_date": "Appointment date / Termin",
    "submission_date": "Submission date / Einreichungsdatum",
    "approval_date": "Approval date / Genehmigungsdatum",
    "rejection_date": "Rejection date / Ablehnungsdatum",
    "created_date": "Created date / Erstellungsdatum",
    "updated_date": "Updated date / Änderungsdatum",
    "organization_name": "Organization name / Organisation",
    "authority_name": "Authority name / Behörde",
    "contact_person": "Contact person / Kontaktperson",
    "website": "Website / Webseite",
    "url": "URL",
    "notes": "Notes / Notizen",
}

FIELD_OPTIONS: tuple[str, ...] = tuple(FIELD_LABELS.keys())

GERMAN_LABEL_MAP: dict[str, str] = {
    "vorname": "given_names",
    "vornamen": "given_names",
    "rufname": "preferred_name",
    "name": "surname",
    "familienname": "surname",
    "nachname": "surname",
    "geburtsname": "birth_name",
    "geburtsdatum": "date_of_birth",
    "geburtsort": "place_of_birth",
    "geburtsland": "country_of_birth",
    "staatsangehörigkeit": "nationality",
    "nationalität": "nationality",
    "geschlecht": "sex",
    "familienstand": "marital_status",
    "anschrift": "address",
    "adresse": "address",
    "straße": "street",
    "strasse": "street",
    "hausnummer": "house_number",
    "postleitzahl": "postal_code",
    "plz": "postal_code",
    "ort": "city",
    "stadt": "city",
    "land": "country",
    "meldeadresse": "registered_address",
    "einzugsdatum": "move_in_date",
    "auszugsdatum": "move_out_date",
    "telefon": "phone_number",
    "telefonnummer": "phone_number",
    "mobil": "mobile_number",
    "mobilnummer": "mobile_number",
    "handynummer": "mobile_number",
    "e-mail": "email",
    "email": "email",
    "passnummer": "passport_number",
    "reisepassnummer": "passport_number",
    "personalausweisnummer": "national_id_number",
    "ausweisnummer": "id_card_number",
    "dokumentnummer": "document_number",
    "ausstellungsdatum": "issue_date",
    "ablaufdatum": "expiry_date",
    "gültig ab": "valid_from",
    "gueltig ab": "valid_from",
    "gültig bis": "valid_until",
    "gueltig bis": "valid_until",
    "ausstellende behörde": "issuing_authority",
    "ausstellende behoerde": "issuing_authority",
    "aktenzeichen": "case_number",
    "referenznummer": "reference_number",
    "vorgangsnummer": "file_number",
    "visum": "visa_type",
    "visumtyp": "visa_type",
    "visumnummer": "visa_number",
    "aufenthaltstitel": "residence_title",
    "aufenthaltstitelnummer": "residence_permit_number",
    "ausländerbehörde": "immigration_authority",
    "auslaenderbehoerde": "immigration_authority",
    "einreisedatum": "entry_date",
    "arbeitserlaubnis": "work_permit",
    "hochschule": "university_name",
    "universität": "university_name",
    "universitaet": "university_name",
    "fakultät": "faculty",
    "fakultaet": "faculty",
    "fachbereich": "department",
    "studierenden-id": "student_id",
    "student id": "student_id",
    "matrikelnummer": "matriculation_number",
    "bewerbernummer": "applicant_number",
    "studiengang": "study_program",
    "abschluss": "degree",
    "semester": "semester",
    "fach": "subject",
    "immatrikulationsdatum": "enrollment_date",
    "exmatrikulationsdatum": "exmatriculation_date",
    "note": "grade",
    "krankenversicherung": "health_insurance_provider",
    "krankenkasse": "health_insurance_provider",
    "krankenversichertennummer": "health_insurance_number",
    "versicherungsnummer": "insurance_number",
    "policennummer": "policy_number",
    "versicherungsbeginn": "insurance_start_date",
    "versicherungsende": "insurance_end_date",
    "sozialversicherungsnummer": "social_security_number",
    "rentenversicherungsnummer": "pension_insurance_number",
    "bank": "bank_name",
    "bankname": "bank_name",
    "kontoinhaber": "account_holder",
    "iban": "iban",
    "bic": "bic",
    "kontonummer": "account_number",
    "bankleitzahl": "bank_code",
    "blz": "bank_code",
    "steuer-id": "tax_id",
    "steuer id": "tax_id",
    "steueridentifikationsnummer": "tax_id",
    "steuernummer": "tax_number",
    "umsatzsteuer-id": "vat_id",
    "betrag": "amount",
    "währung": "currency",
    "waehrung": "currency",
    "rechnungsnummer": "invoice_number",
    "kundennummer": "customer_number",
    "vertragsnummer": "contract_number",
    "verwendungszweck": "payment_reference",
    "arbeitgeber": "employer",
    "arbeitgebername": "employer_name",
    "arbeitnehmer": "employee",
    "mitarbeiter": "employee",
    "personalnummer": "employee_id",
    "berufsbezeichnung": "job_title",
    "position": "position",
    "abteilung": "department_work",
    "beschäftigungsart": "employment_type",
    "beschaeftigungsart": "employment_type",
    "vertragsbeginn": "contract_start_date",
    "vertragsende": "contract_end_date",
    "beginn": "start_date",
    "eintritt": "start_date",
    "ende": "end_date",
    "austritt": "end_date",
    "probezeit": "probation_end_date",
    "gehalt": "salary",
    "vergütung": "salary",
    "verguetung": "salary",
    "bruttogehalt": "gross_salary",
    "nettogehalt": "net_salary",
    "stundenlohn": "hourly_wage",
    "arbeitszeit": "working_hours",
    "wochenstunden": "weekly_hours",
    "urlaubstage": "vacation_days",
    "vermieter": "landlord_name",
    "mieter": "tenant_name",
    "mietadresse": "rental_address",
    "miete": "rent_amount",
    "kaltmiete": "cold_rent",
    "warmmiete": "warm_rent",
    "kaution": "deposit_amount",
    "mietbeginn": "rental_contract_start_date",
    "mietende": "rental_contract_end_date",
    "zimmernummer": "room_number",
    "wohnungsnummer": "apartment_number",
    "datum": "date",
    "frist": "deadline",
    "termin": "appointment_date",
    "einreichungsdatum": "submission_date",
    "genehmigungsdatum": "approval_date",
    "ablehnungsdatum": "rejection_date",
    "erstellungsdatum": "created_date",
    "änderungsdatum": "updated_date",
    "aenderungsdatum": "updated_date",
    "organisation": "organization_name",
    "behörde": "authority_name",
    "behoerde": "authority_name",
    "kontaktperson": "contact_person",
    "webseite": "website",
    "notizen": "notes",
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
    ("0% - 50%", 0.00, 0.50),
)


def _active_entity_id() -> str | None:
    try:
        from ui.state import session_manager as sm
        from ui.state.session_keys import SessionKeys

        val = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
        if val is not None and str(val).strip():
            return str(val)
    except Exception:
        pass

    try:
        conn = _get_db().connection
        row = conn.execute("""
            SELECT entity_id
            FROM review_cases
            ORDER BY created_at DESC
            LIMIT 1
            """).fetchone()
        if row and row["entity_id"]:
            return str(row["entity_id"])
    except Exception:
        pass

    try:
        conn = _get_db().connection
        row = conn.execute("""
            SELECT entity_id
            FROM facts
            ORDER BY created_at DESC
            LIMIT 1
            """).fetchone()
        if row and row["entity_id"]:
            return str(row["entity_id"])
    except Exception:
        pass

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

        pending = count(
            "entity_id = ? AND UPPER(status) = 'PENDING'",
            (entity_id,),
        )
        accepted = count(
            "entity_id = ? AND UPPER(status) IN ('COMPLETED', 'ACCEPTED')",
            (entity_id,),
        )
        rejected = count(
            "entity_id = ? AND UPPER(status) IN ('CANCELLED', 'REJECTED')",
            (entity_id,),
        )
        visible = count(
            """
            entity_id = ?
            AND UPPER(status) = 'PENDING'
            AND confidence >= 0.5
            AND fact_type NOT IN ('review_candidate', 'bic')
            """,
            (entity_id,),
        )
        hidden_for_llm = count(
            """
            entity_id = ?
            AND UPPER(status) = 'PENDING'
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
                "UPPER(status) = 'PENDING'",
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
              AND UPPER(status) = 'PENDING'
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
        owner_selection: OwnerSelection | None = None,
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

                self._accept_fact_from_case(case, field_name, value, actor, owner_selection)

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
        owner_selection: OwnerSelection | None = None,
    ) -> DecisionResult:
        return self.submit_decision(
            case_id, decision, actor, edited_value, edited_field, owner_selection
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


    def _normalize_name(self, value: str) -> str:
        return " ".join(str(value or "").strip().split())

    def _new_relationship_id(self) -> str:
        import uuid
        return f"REL-{uuid.uuid4().hex.upper()}"

    def _resolve_target_entity_id(
        self,
        active_entity_id: str,
        owner_selection: OwnerSelection | None,
    ) -> tuple[str, dict[str, Any]]:
        if owner_selection is None or owner_selection.target == OwnerTarget.ACTIVE_ENTITY:
            return active_entity_id, {
                "owner_target": "active_entity",
                "owner_entity_id": active_entity_id,
                "owner_type": "person",
                "owner_name": "",
                "relation_type": "self",
            }

        owner_name = self._normalize_name(owner_selection.owner_name)
        owner_type = self._normalize_name(owner_selection.owner_type) or "unknown_organization"
        relation_type = self._normalize_name(owner_selection.relation_type) or "other"

        if not owner_name:
            raise ValueError("Owner name is required for external entity")

        conn = _get_db().connection
        row = conn.execute(
            """
            SELECT entity_id
            FROM entities
            WHERE LOWER(display_name) = LOWER(?)
              AND entity_type = ?
              AND status = 'active'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (owner_name, owner_type),
        ).fetchone()

        now = utcnow_iso()

        if row:
            target_entity_id = str(row["entity_id"])
        else:
            target_entity_id = str(generate_entity_id())
            conn.execute(
                """
                INSERT INTO entities (
                    entity_id,
                    entity_type,
                    display_name,
                    status,
                    created_at,
                    updated_at,
                    primary_language,
                    merged_into,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_entity_id,
                    owner_type,
                    owner_name,
                    "active",
                    now,
                    now,
                    "en",
                    None,
                    json.dumps(
                        {
                            "created_from": "human_review",
                            "active_entity_id": active_entity_id,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )

        if target_entity_id != active_entity_id:
            existing_rel = conn.execute(
                """
                SELECT relationship_id
                FROM entity_relationships
                WHERE source_entity_id = ?
                  AND target_entity_id = ?
                  AND relation_type = ?
                LIMIT 1
                """,
                (active_entity_id, target_entity_id, relation_type),
            ).fetchone()

            if not existing_rel:
                conn.execute(
                    """
                    INSERT INTO entity_relationships (
                        relationship_id,
                        source_entity_id,
                        target_entity_id,
                        relation_type,
                        confidence,
                        created_at,
                        metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._new_relationship_id(),
                        active_entity_id,
                        target_entity_id,
                        relation_type,
                        1.0,
                        now,
                        json.dumps(
                            {
                                "created_from": "human_review",
                                "owner_name": owner_name,
                                "owner_type": owner_type,
                            },
                            ensure_ascii=False,
                        ),
                    ),
                )

        return target_entity_id, {
            "owner_target": "external_entity",
            "owner_entity_id": target_entity_id,
            "owner_type": owner_type,
            "owner_name": owner_name,
            "relation_type": relation_type,
        }

    def _accept_fact_from_case(
        self,
        case: ReviewCase,
        field_name: str,
        value: str,
        actor: str,
        owner_selection: OwnerSelection | None = None,
    ) -> None:
        db = _get_db()
        conn = db.connection

        metadata = dict(case.metadata)
        active_entity_id = str(case.entity_id)
        target_entity_id, owner_metadata = self._resolve_target_entity_id(active_entity_id, owner_selection)
        existing_fact_id = str(metadata.get("fact_id") or "").strip()
        accepted_at = utcnow_iso()

        if existing_fact_id:
            row = conn.execute(
                "SELECT fact_id FROM facts WHERE fact_id = ?",
                (existing_fact_id,),
            ).fetchone()

            if row:
                conn.execute(
                    """
                    UPDATE facts
                    SET field_name = ?,
                        canonical_value = ?,
                        display_value = ?,
                        value_type = 'string',
                        confidence = ?,
                        status = 'accepted',
                        source_stage = 'human_review',
                        accepted_at = ?,
                        accepted_by = ?,
                        metadata = ?
                    WHERE fact_id = ?
                    """,
                    (
                        field_name,
                        value,
                        value,
                        float(case.confidence),
                        accepted_at,
                        actor,
                        json.dumps(
                            {
                                **metadata,
                                "review_case_id": str(case.review_case_id),
                                "candidate_fact_id": str(case.candidate_fact_id),
                                "accepted_from_review": True,
                                **owner_metadata,
                            },
                            ensure_ascii=False,
                        ),
                        existing_fact_id,
                    ),
                )
                conn.commit()
                return

        fact_id = str(generate_fact_id())

        conn.execute(
            """
            INSERT INTO facts (
                fact_id,
                entity_id,
                field_name,
                canonical_value,
                display_value,
                value_type,
                confidence,
                status,
                source_stage,
                created_at,
                accepted_at,
                accepted_by,
                superseded_by,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                target_entity_id,
                field_name,
                value,
                value,
                "string",
                float(case.confidence),
                "accepted",
                "human_review",
                accepted_at,
                accepted_at,
                actor,
                None,
                json.dumps(
                    {
                        **metadata,
                        "review_case_id": str(case.review_case_id),
                        "candidate_fact_id": str(case.candidate_fact_id),
                        "accepted_from_review": True,
                        "original_fact_type": str(case.fact_type),
                        "original_raw_value": str(case.raw_value),
                        "original_normalized_value": str(case.normalized_value),
                        **owner_metadata,
                    },
                    ensure_ascii=False,
                ),
            ),
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
