from __future__ import annotations

import hashlib
import re
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
    _get_db,
    ensure_background_pipeline_running,
    get_conflict_repo,
    get_document_repo,
    get_pipeline_service,
    get_review_repo,
)
from ui.viewmodels.document_models import DocumentDetail, DocumentSummary, UploadResult


def _active_entity_id() -> str | None:
    try:
        from ui.state import session_manager as sm
        from ui.state.session_keys import SessionKeys

        value = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
        return str(value) if value is not None else None
    except Exception:
        return None


def _safe_status(status: Any) -> str:
    text = str(status)
    if "." in text:
        text = text.split(".")[-1]
    return text.lower()


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9äöüß\s:/.-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _score_keywords(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _detect_doc_type_from_text(text: str) -> str:
    normalized = _normalize_text(text)

    keyword_map: dict[str, tuple[str, ...]] = {
        "passport": (
            "passport",
            "reisepass",
            "document no",
            "passport no",
            "nationality",
            "place of birth",
            "date of birth",
            "issuing authority",
        ),
        "id_card": (
            "identity card",
            "id card",
            "personalausweis",
            "national identity",
            "ausweis",
            "identity number",
        ),
        "residence_permit": (
            "residence permit",
            "aufenthaltstitel",
            "aufenthaltserlaubnis",
            "residence card",
            "permit",
            "gültig bis",
        ),
        "bank_statement": (
            "bank statement",
            "kontoauszug",
            "iban",
            "bic",
            "account number",
            "balance",
            "transaction",
            "booking date",
        ),
        "contract": (
            "contract",
            "agreement",
            "vertrag",
            "employment contract",
            "internship agreement",
            "employee",
            "employer",
            "salary",
            "working hours",
        ),
        "invoice": (
            "invoice",
            "rechnung",
            "tax",
            "vat",
            "total amount",
            "amount due",
            "invoice number",
            "ust-id",
        ),
        "certificate": (
            "certificate",
            "zertifikat",
            "bescheinigung",
            "awarded",
            "completed",
            "successfully completed",
            "course",
            "training",
        ),
        "insurance": (
            "insurance",
            "versicherung",
            "policy",
            "insured",
            "coverage",
            "krankenversicherung",
        ),
    }

    scores = {
        doc_type: _score_keywords(normalized, keywords)
        for doc_type, keywords in keyword_map.items()
    }

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score <= 0:
        return "other"

    return best_type


def _to_summary(doc: Document) -> DocumentSummary:
    return DocumentSummary(
        document_id=str(doc.document_id),
        file_name=Path(str(doc.file_path)).name,
        document_type=str(doc.doc_type),
        status=_safe_status(doc.status),
        confidence=doc.metadata.get("confidence"),
    )


def _to_detail(
    doc: Document,
    conflict_count: int,
    review_required: bool,
) -> DocumentDetail:
    return DocumentDetail(
        document_id=str(doc.document_id),
        file_name=Path(str(doc.file_path)).name,
        document_type=str(doc.doc_type),
        status=_safe_status(doc.status),
        created_at=str(doc.created_at)[:19] if doc.created_at else "",
        page_count=int(doc.metadata.get("page_count", 0) or 0),
        extracted_fields_count=int(doc.metadata.get("extracted_fields_count", 0) or 0),
        conflict_count=conflict_count,
        review_required=review_required,
        confidence=doc.metadata.get("confidence"),
        preview_text=str(doc.metadata.get("preview_text", "") or ""),
    )


def _extract_metadata_from_job(job: Job) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    try:
        ocr_artifacts = job.context.artifacts.by_type(ArtifactType.OCR)
        if ocr_artifacts:
            artifact = ocr_artifacts[-1]
            if isinstance(artifact, OcrArtifact):
                full_text = str((artifact.snapshot or {}).get("full_text", "") or "")
                metadata["page_count"] = artifact.page_count
                metadata["confidence"] = round(float(artifact.mean_confidence), 4)
                metadata["preview_text"] = full_text[:1500]
                metadata["source_id"] = str(artifact.source_id)
                metadata["ocr_text_length"] = len(full_text)
                metadata["detected_doc_type"] = _detect_doc_type_from_text(full_text)

        extraction_artifacts = job.context.artifacts.by_type(ArtifactType.EXTRACTION)
        if extraction_artifacts:
            artifact = extraction_artifacts[-1]
            if isinstance(artifact, ExtractionArtifact):
                metadata["extracted_fields_count"] = artifact.candidate_fact_count
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
        messages = [failure.message for failure in job.context.failures.all()]
        return "; ".join(messages)
    except Exception:
        return ""


def _write_uploaded_file(entity_id: str, file_name: str, file_bytes: bytes) -> Path:
    safe_name = Path(file_name).name
    digest = hashlib.sha256(file_bytes).hexdigest()[:16]
    entity_dir = UPLOADS_DIR / entity_id
    entity_dir.mkdir(parents=True, exist_ok=True)
    destination = entity_dir / f"{digest}_{safe_name}"
    destination.write_bytes(file_bytes)
    return destination


def _commit() -> None:
    _get_db().connection.commit()


def _submit_llm_extraction_job(
    document_id: str,
    entity_id: str,
    metadata: dict[str, Any],
) -> str | None:
    raw_text = str(metadata.get("preview_text") or "").strip()
    source_id = str(metadata.get("source_id") or "").strip()

    if not raw_text:
        return None

    try:
        ensure_background_pipeline_running()

        job = Job.create(
            job_type=JobType.LLM_EXTRACTION,
            payload={
                "stage": "llm",
                "document_id": document_id,
                "entity_id": entity_id,
                "source_id": source_id,
                "raw_text": raw_text,
            },
            priority=JobPriority.LOW,
            max_retries=2,
        )

        get_pipeline_service().submit(job)
        return job.job_id
    except Exception:
        return None


class DocumentsVM:

    def load_documents(self) -> tuple[DocumentSummary, ...]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return ()

        try:
            docs = get_document_repo().list_by_entity(EntityId(entity_id))
            return tuple(_to_summary(doc) for doc in docs)
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
            conflicts = get_conflict_repo().list_by_entity(EntityId(entity_id))
            conflict_count = sum(
                1 for conflict in conflicts if conflict.status == ConflictStatus.OPEN
            )

            pending_cases = get_review_repo().list_by_status(ReviewStatus.PENDING)
            review_required = (
                len(
                    [case for case in pending_cases if str(case.entity_id) == entity_id]
                )
                > 0
            )

            return _to_detail(
                doc=doc,
                conflict_count=conflict_count,
                review_required=review_required,
            )
        except Exception:
            return None

    def upload_document(
        self,
        file_bytes: bytes,
        file_name: str,
        language: str = "en",
    ) -> UploadResult:
        repo = get_document_repo()
        doc: Document | None = None

        try:
            entity_id = _active_entity_id()
            if entity_id is None:
                return UploadResult(
                    success=False,
                    message="No active entity selected.",
                )

            if not file_bytes:
                return UploadResult(
                    success=False,
                    message="Uploaded file is empty.",
                )

            file_hash = hashlib.sha256(file_bytes).hexdigest()
            existing = repo.get_by_hash(file_hash)

            if existing is not None and str(existing.entity_id) == entity_id:
                return UploadResult(
                    success=True,
                    document_id=str(existing.document_id),
                    message="Document already exists for this entity.",
                )

            destination = _write_uploaded_file(entity_id, file_name, file_bytes)
            document_id = DocumentId(str(generate_document_id()))

            doc = Document(
                document_id=document_id,
                entity_id=EntityId(entity_id),
                doc_type="other",
                file_hash=file_hash,
                file_path=str(destination),
                language=language,
                status=DocumentStatus.PENDING,
                created_at=utcnow_iso(),
                issued_at=None,
                expires_at=None,
                metadata={
                    "original_file_name": file_name,
                    "stored_file_name": destination.name,
                    "upload_stage": "intake",
                    "initial_doc_type": "other",
                },
            )

            repo.save(doc)
            _commit()

            doc.start_processing()
            repo.save(doc)
            _commit()

            job = Job.create(
                job_type=JobType.DOCUMENT_PIPELINE,
                payload={"document": doc.to_dict()},
                priority=JobPriority.NORMAL,
            )

            _get_container().sequential_pipeline_handler.handle(job)

            metadata = _extract_metadata_from_job(job)

            llm_job_id = _submit_llm_extraction_job(
                document_id=str(document_id),
                entity_id=entity_id,
                metadata=metadata,
            )

            if llm_job_id:
                metadata["llm_job_id"] = llm_job_id
                metadata["llm_status"] = "pending"

            has_knowledge = _has_persisted_knowledge(entity_id)
            has_metadata = bool(metadata)

            if (
                job.context.failures.has_critical()
                and not has_knowledge
                and not has_metadata
            ):
                failure_message = _failure_messages(job)
                doc.mark_failed()
                doc.metadata["pipeline_error"] = failure_message
                repo.save(doc)
                _commit()
                return UploadResult(
                    success=False,
                    document_id=str(document_id),
                    message=f"Pipeline failed: {failure_message}",
                )

            if job.context.failures.has_critical():
                metadata["pipeline_warnings"] = _failure_messages(job)

            detected_doc_type = str(metadata.get("detected_doc_type") or "other")
            doc.doc_type = detected_doc_type
            doc.metadata.update(metadata)
            doc.mark_processed()
            repo.save(doc)
            _commit()

            return UploadResult(
                success=True,
                document_id=str(document_id),
                message="Document processed.",
            )

        except Exception as exc:
            if doc is not None:
                try:
                    doc.mark_failed()
                    doc.metadata["pipeline_error"] = str(exc)
                    repo.save(doc)
                    _commit()
                except Exception:
                    pass

            return UploadResult(
                success=False,
                document_id=str(doc.document_id) if doc is not None else "",
                message=str(exc),
            )
