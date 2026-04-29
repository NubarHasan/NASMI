from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocumentType(Enum):
    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    RESIDENCE_PERMIT = "residence_permit"
    MELDEBESCHEINIGUNG = "meldebescheinigung"
    PAYSLIP = "payslip"
    TAX_ASSESSMENT = "tax_assessment"
    SOCIAL_SECURITY = "social_security"
    RENTAL_CONTRACT = "rental_contract"
    BANK_STATEMENT = "bank_statement"
    INSURANCE = "insurance"
    UNKNOWN = "unknown"


@dataclass
class FieldSchema:
    doc_type: DocumentType
    required: list[str]
    optional: list[str]
    frozen: list[str]
    keywords: list[str]
    has_expiry: bool = False

    def all_fields(self) -> list[str]:
        return self.required + self.optional

    def coverage(self, extracted: dict) -> float:
        if not self.required:
            return 1.0
        filled = sum(1 for f in self.required if extracted.get(f))
        return round(filled / len(self.required), 2)


SCHEMAS: dict[DocumentType, FieldSchema] = {
    DocumentType.PASSPORT: FieldSchema(
        doc_type=DocumentType.PASSPORT,
        required=[
            "full_name",
            "passport_number",
            "date_of_birth",
            "nationality",
            "issue_date",
            "expiry_date",
        ],
        optional=["place_of_birth", "gender", "mrz_line1", "mrz_line2"],
        frozen=["full_name", "date_of_birth", "nationality"],
        keywords=[
            "reisepass",
            "passport",
            "passeport",
            "mrz",
            "nationality",
            "staatsangehörigkeit",
        ],
        has_expiry=True,
    ),
    DocumentType.NATIONAL_ID: FieldSchema(
        doc_type=DocumentType.NATIONAL_ID,
        required=[
            "full_name",
            "id_number",
            "date_of_birth",
            "issue_date",
            "expiry_date",
        ],
        optional=["address", "place_of_birth", "gender", "height"],
        frozen=["full_name", "date_of_birth", "id_number"],
        keywords=[
            "personalausweis",
            "national id",
            "ausweis",
            "identity card",
            "carte",
        ],
        has_expiry=True,
    ),
    DocumentType.RESIDENCE_PERMIT: FieldSchema(
        doc_type=DocumentType.RESIDENCE_PERMIT,
        required=[
            "full_name",
            "permit_number",
            "permit_type",
            "issue_date",
            "expiry_date",
            "issuing_authority",
        ],
        optional=["nationality", "date_of_birth", "conditions"],
        frozen=["full_name", "date_of_birth"],
        keywords=[
            "aufenthaltstitel",
            "niederlassungserlaubnis",
            "aufenthaltserlaubnis",
            "residence permit",
            "visum",
        ],
        has_expiry=True,
    ),
    DocumentType.MELDEBESCHEINIGUNG: FieldSchema(
        doc_type=DocumentType.MELDEBESCHEINIGUNG,
        required=["full_name", "address", "registration_date", "issuing_authority"],
        optional=["date_of_birth", "nationality", "previous_address"],
        frozen=["full_name", "date_of_birth"],
        keywords=[
            "meldebescheinigung",
            "anmeldung",
            "einwohnermeldeamt",
            "hauptwohnung",
            "nebenwohnung",
            "gemeldet",
        ],
        has_expiry=False,
    ),
    DocumentType.PAYSLIP: FieldSchema(
        doc_type=DocumentType.PAYSLIP,
        required=["full_name", "employer", "gross_amount", "net_amount", "pay_date"],
        optional=[
            "tax_id",
            "social_security_number",
            "iban",
            "tax_class",
            "working_hours",
            "deductions",
        ],
        frozen=["full_name"],
        keywords=[
            "lohnabrechnung",
            "gehaltsabrechnung",
            "entgeltabrechnung",
            "brutto",
            "netto",
            "arbeitgeber",
            "payslip",
        ],
        has_expiry=False,
    ),
    DocumentType.TAX_ASSESSMENT: FieldSchema(
        doc_type=DocumentType.TAX_ASSESSMENT,
        required=["full_name", "tax_id", "tax_year", "taxable_income", "tax_amount"],
        optional=["refund_amount", "payment_due", "issuing_office"],
        frozen=["full_name", "tax_id"],
        keywords=[
            "steuerbescheid",
            "einkommensteuer",
            "finanzamt",
            "steueridentifikationsnummer",
            "veranlagungszeitraum",
        ],
        has_expiry=False,
    ),
    DocumentType.SOCIAL_SECURITY: FieldSchema(
        doc_type=DocumentType.SOCIAL_SECURITY,
        required=["full_name", "social_security_number", "date_of_birth"],
        optional=["issuing_authority", "issue_date"],
        frozen=["full_name", "date_of_birth", "social_security_number"],
        keywords=[
            "sozialversicherungsausweis",
            "rentenversicherung",
            "sozialversicherungsnummer",
            "krankenkasse",
        ],
        has_expiry=False,
    ),
    DocumentType.RENTAL_CONTRACT: FieldSchema(
        doc_type=DocumentType.RENTAL_CONTRACT,
        required=["full_name", "landlord", "address", "rent_amount", "contract_start"],
        optional=[
            "contract_end",
            "deposit",
            "iban",
            "utilities_included",
            "floor_area",
        ],
        frozen=[],
        keywords=[
            "mietvertrag",
            "mieter",
            "vermieter",
            "kaltmiete",
            "warmmiete",
            "nebenkosten",
            "rental agreement",
        ],
        has_expiry=False,
    ),
    DocumentType.BANK_STATEMENT: FieldSchema(
        doc_type=DocumentType.BANK_STATEMENT,
        required=["full_name", "iban", "bank_name", "statement_date", "balance"],
        optional=["bic", "account_number", "transactions"],
        frozen=[],
        keywords=[
            "kontoauszug",
            "kontonummer",
            "iban",
            "bic",
            "bank statement",
            "girokonto",
            "sparkasse",
            "volksbank",
        ],
        has_expiry=False,
    ),
    DocumentType.INSURANCE: FieldSchema(
        doc_type=DocumentType.INSURANCE,
        required=[
            "full_name",
            "policy_number",
            "insurance_type",
            "provider",
            "start_date",
        ],
        optional=["end_date", "premium", "coverage_amount", "beneficiary"],
        frozen=[],
        keywords=[
            "versicherung",
            "versicherungsschein",
            "police",
            "krankenversicherung",
            "haftpflicht",
            "insurance",
        ],
        has_expiry=True,
    ),
    DocumentType.UNKNOWN: FieldSchema(
        doc_type=DocumentType.UNKNOWN,
        required=[],
        optional=[],
        frozen=[],
        keywords=[],
        has_expiry=False,
    ),
}


def get_schema(doc_type: DocumentType) -> FieldSchema:
    return SCHEMAS.get(doc_type, SCHEMAS[DocumentType.UNKNOWN])


def detect_type_by_keywords(text: str) -> tuple[DocumentType, float]:
    text_lower = text.lower()
    scores: dict[DocumentType, int] = {}

    for doc_type, schema in SCHEMAS.items():
        if doc_type == DocumentType.UNKNOWN:
            continue
        hits = sum(1 for kw in schema.keywords if kw in text_lower)
        if hits:
            scores[doc_type] = hits

    if not scores:
        return DocumentType.UNKNOWN, 0.0

    best = max(scores, key=lambda k: scores[k])
    total_kw = len(SCHEMAS[best].keywords)
    confidence = round(scores[best] / total_kw, 2)

    return best, confidence
