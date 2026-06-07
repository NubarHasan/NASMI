from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentSummary:
    document_id: str
    file_name: str
    document_type: str
    status: str
    confidence: float | None = None


@dataclass(frozen=True)
class DocumentDetail:
    document_id: str
    file_name: str
    document_type: str
    status: str
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
