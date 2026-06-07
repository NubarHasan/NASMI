from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from archive.document import Document, DocumentStatus
from core.identifiers import generate_document_id
from core.paths import UPLOADS_DIR
from core.time import utcnow_iso
from core.types import DocumentId, EntityId
from knowledge.conflict import ConflictStatus
from pipeline.artifact import ArtifactType, ExtractionArtifact, OcrArtifact
from pipeline.job import Job, JobPriority, JobType
from review.review_type import ReviewStatus
from ui.services.api_client import (
    _get_container,
    get_conflict_repo,
    get_document_repo,
    get_review_repo,
)
from ui.viewmodels.document_models import DocumentDetail, DocumentSummary, UploadResult


def _active_entity_id() -> str | None:
    try:
        from ui.state import session_manager as sm
        from ui.state.session_keys import SessionKeys

        val = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
        return str(val) if val is not None else None
    except Exception:
        return None


def _detect_doc_type(file_name: str) -> str:
    name = file_name.lower()
    if "passport" in name:
        return "passport"
    if "id" in name or "national" in name:
        return "id_card"
    if "residence" in name:
        return "residence_permit"
    if "bank" in name or "statement" in name:
        return "bank_statement"
    if "contract" in name:
        return "contract"
    if "invoice" in name:
        return "invoice"
    if "certificate" in name or "cert" in name:
        return "certificate"
    return "passport"


def _to_summary(doc: Document) -> DocumentSummary:
    return DocumentSummary(
        document_id=str(doc.document_id),
        file_name=Path(doc.file_path).name,
        document_type=doc.doc_type,
        status=str(doc.status),
        confidence=doc.metadata.get("confidence"),
    )


def _to_detail(
    doc: Document, conflict_count: int, review_required: bool
) -> DocumentDetail:
    return DocumentDetail(
        document_id=str(doc.document_id),
        file_name=Path(doc.file_path).name,
        document_type=doc.doc_type,
        status=str(doc.status),
        created_at=doc.created_at[:10] if doc.created_at else "",
        page_count=int(doc.metadata.get("page_count", 0)),
        extracted_fields_count=int(doc.metadata.get("extracted_fields_count", 0)),
        conflict_count=conflict_count,
        review_required=review_required,
        confidence=doc.metadata.get("confidence"),
        preview_text=str(doc.metadata.get("preview_text", "")),
    )


def _extract_metadata_from_job(job: Job) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    try:
        ocr_list = job.context.artifacts.by_type(ArtifactType.OCR)
        if ocr_list:
            raw_ocr = ocr_list[-1]
            if isinstance(raw_ocr, OcrArtifact):
                metadata["page_count"] = raw_ocr.page_count
                metadata["confidence"] = round(raw_ocr.mean_confidence, 4)
                metadata["preview_text"] = (raw_ocr.snapshot or {}).get(
                    "full_text", ""
                )[:500]

        ext_list = job.context.artifacts.by_type(ArtifactType.EXTRACTION)
        if ext_list:
            raw_ext = ext_list[-1]
            if isinstance(raw_ext, ExtractionArtifact):
                metadata["extracted_fields_count"] = raw_ext.candidate_fact_count
    except Exception:
        pass
    return metadata


def _has_persisted_knowledge(entity_id: str) -> bool:
    try:
        facts = _get_container().knowledge_app_service.list_facts_by_entity(
            EntityId(entity_id)
        )
        return len(facts) > 0
    except Exception:
        return False


def _failure_messages(job: Job) -> str:
    try:
        return "; ".join(f.message for f in job.context.failures.all())
    except Exception:
        return ""


class DocumentsVM:

    def load_documents(self) -> tuple[DocumentSummary, ...]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return ()
        try:
            docs = get_document_repo().list_by_entity(EntityId(entity_id))
            return tuple(_to_summary(d) for d in docs)
        except Exception:
            return ()

    def refresh_documents(self) -> tuple[DocumentSummary, ...]:
        return self.load_documents()

    def load_document(self, document_id: str) -> DocumentDetail | None:
        try:
            doc = get_document_repo().get(DocumentId(document_id))
            if doc is None:
                return None
            entity_id = str(doc.entity_id)
            all_conflicts = get_conflict_repo().list_by_entity(EntityId(entity_id))
            conflict_count = sum(
                1 for c in all_conflicts if c.status == ConflictStatus.OPEN
            )
            pending_cases = get_review_repo().list_by_status(ReviewStatus.PENDING)
            review_required = len(pending_cases) > 0
            return _to_detail(doc, conflict_count, review_required)
        except Exception:
            return None

    def upload_document(
        self, file_bytes: bytes, file_name: str, doc_type: str | None
    ) -> UploadResult:
        repo = get_document_repo()
        doc: Document | None = None

        try:
            entity_id = _active_entity_id()
            if entity_id is None:
                return UploadResult(success=False, message="No active entity selected.")

            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPLOADS_DIR / file_name
            dest.write_bytes(file_bytes)

            file_hash = hashlib.sha256(file_bytes).hexdigest()
            doc_id = DocumentId(str(generate_document_id()))
            resolved_doc_type = doc_type or _detect_doc_type(file_name)

            doc = Document(
                document_id=doc_id,
                entity_id=EntityId(entity_id),
                doc_type=resolved_doc_type,
                file_hash=file_hash,
                file_path=str(dest),
                language="en",
                status=DocumentStatus.PENDING,
                created_at=utcnow_iso(),
                issued_at=None,
                expires_at=None,
                metadata={},
            )
            repo.save(doc)

            doc.start_processing()
            repo.save(doc)

            job = Job.create(
                job_type=JobType.DOCUMENT_PIPELINE,
                payload={"document": doc.to_dict()},
                priority=JobPriority.NORMAL,
            )
            _get_container().sequential_pipeline_handler.handle(job)

            metadata = _extract_metadata_from_job(job)
            has_knowledge = _has_persisted_knowledge(entity_id)
            has_metadata = bool(metadata)

            if (
                job.context.failures.has_critical()
                and not has_knowledge
                and not has_metadata
            ):
                failure_messages = _failure_messages(job)
                doc.mark_failed()
                repo.save(doc)
                return UploadResult(
                    success=False,
                    message=f"Pipeline failed: {failure_messages}",
                )

            if job.context.failures.has_critical():
                metadata["pipeline_warnings"] = _failure_messages(job)

            doc.metadata.update(metadata)
            doc.mark_processed()
            repo.save(doc)

            return UploadResult(success=True, document_id=str(doc_id))

        except Exception as exc:
            if doc is not None:
                try:
                    if doc.status == DocumentStatus.PROCESSING:
                        doc.mark_failed()
                        repo.save(doc)
                except Exception:
                    pass
            return UploadResult(success=False, message=str(exc))
