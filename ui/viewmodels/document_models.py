from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DocumentType(StrEnum):
    PASSPORT = "passport"
    RESIDENCE_PERMIT = "residence_permit"
    NATIONAL_ID = "national_id"
    DRIVING_LICENSE = "driving_license"
    TAX_DOCUMENT = "tax_document"
    INSURANCE_DOCUMENT = "insurance_document"
    EMPLOYMENT_CONTRACT = "employment_contract"
    PAYSLIP = "payslip"
    BANK_STATEMENT = "bank_statement"
    INVOICE = "invoice"
    UNIVERSITY_CERTIFICATE = "university_certificate"
    BIRTH_CERTIFICATE = "birth_certificate"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    RENTAL_CONTRACT = "rental_contract"
    ENERGY_BILL = "energy_bill"
    ELECTRICITY_CONTRACT = "electricity_contract"
    WATER_BILL = "water_bill"
    INTERNET_CONTRACT = "internet_contract"
    PHONE_CONTRACT = "phone_contract"
    CHILD_BENEFIT = "child_benefit"
    UNEMPLOYMENT_BENEFIT = "unemployment_benefit"
    RESIDENCE_REGISTRATION = "residence_registration"
    OTHER = "other"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class DocumentSummary:
    document_id: str
    file_name: str
    document_type: DocumentType
    status: DocumentStatus
    confidence: float | None = None


@dataclass(frozen=True)
class DocumentDetail:
    document_id: str
    file_name: str
    document_type: DocumentType
    status: DocumentStatus
    created_at: str
    page_count: int
    extracted_fields_count: int
    conflict_count: int
    review_required: bool
    confidence: float | None = None
    preview_text: str = ""


@dataclass(frozen=True)
class UploadResult:
    success: bool
    document_id: str = ""
    message: str = ""
