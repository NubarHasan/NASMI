from __future__ import annotations

import uuid

from ui.viewmodels.document_models import (
    DocumentDetail,
    DocumentStatus,
    DocumentSummary,
    DocumentType,
    UploadResult,
)

_MOCK_DOCUMENTS: tuple[DocumentSummary, ...] = (
    DocumentSummary(
        "doc-001",
        "nubar_passport.pdf",
        DocumentType.PASSPORT,
        DocumentStatus.REVIEWED,
        0.97,
    ),
    DocumentSummary(
        "doc-002",
        "nubar_residence_permit.pdf",
        DocumentType.RESIDENCE_PERMIT,
        DocumentStatus.REVIEWED,
        0.93,
    ),
    DocumentSummary(
        "doc-003",
        "nubar_employment_contract.pdf",
        DocumentType.EMPLOYMENT_CONTRACT,
        DocumentStatus.PENDING,
        0.88,
    ),
    DocumentSummary(
        "doc-004",
        "nubar_bank_statement_q1.pdf",
        DocumentType.BANK_STATEMENT,
        DocumentStatus.PROCESSING,
        0.81,
    ),
    DocumentSummary(
        "doc-005",
        "nubar_payslip_march.pdf",
        DocumentType.PAYSLIP,
        DocumentStatus.PENDING,
        None,
    ),
)

_MOCK_DETAILS: dict[str, DocumentDetail] = {
    "doc-001": DocumentDetail(
        document_id="doc-001",
        file_name="nubar_passport.pdf",
        document_type=DocumentType.PASSPORT,
        status=DocumentStatus.REVIEWED,
        created_at="2025-11-14",
        page_count=2,
        extracted_fields_count=8,
        conflict_count=0,
        review_required=False,
        confidence=0.97,
        preview_text="Passport No: A12345678 · DOB: 1990-03-22 · Expiry: 2030-03-21",
    ),
    "doc-002": DocumentDetail(
        document_id="doc-002",
        file_name="nubar_residence_permit.pdf",
        document_type=DocumentType.RESIDENCE_PERMIT,
        status=DocumentStatus.REVIEWED,
        created_at="2025-11-20",
        page_count=1,
        extracted_fields_count=6,
        conflict_count=1,
        review_required=True,
        confidence=0.93,
        preview_text="Permit No: RP-2025-009821 · Valid Until: 2027-11-19 · Issuer: Immigration Authority",
    ),
    "doc-003": DocumentDetail(
        document_id="doc-003",
        file_name="nubar_employment_contract.pdf",
        document_type=DocumentType.EMPLOYMENT_CONTRACT,
        status=DocumentStatus.PENDING,
        created_at="2026-01-05",
        page_count=4,
        extracted_fields_count=11,
        conflict_count=0,
        review_required=False,
        confidence=0.88,
        preview_text="Employer: TechCorp GmbH · Position: Software Engineer · Start: 2026-02-01",
    ),
}


class DocumentsVM:
    def load_documents(self) -> tuple[DocumentSummary, ...]:
        return _MOCK_DOCUMENTS

    def refresh_documents(self) -> tuple[DocumentSummary, ...]:
        return self.load_documents()

    def load_document(self, document_id: str) -> DocumentDetail | None:
        return _MOCK_DETAILS.get(document_id)

    def upload_document(
        self, file_name: str, document_type: DocumentType
    ) -> UploadResult:
        return UploadResult(
            success=True,
            document_id=f"doc-{uuid.uuid4().hex[:8]}",
        )
