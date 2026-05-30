from __future__ import annotations

from pathlib import Path

from core.constants import DATABASE_FILENAME
from core.types import (
    DirectoryPath,
    DocumentId,
    EntityId,
    FilePath,
    JobId,
    KnowledgeId,
    PackageId,
)

BASE_DIR: DirectoryPath = Path(__file__).resolve().parent.parent
DATA_DIR: DirectoryPath = BASE_DIR / "data"
LOGS_DIR: DirectoryPath = BASE_DIR / "logs"
TEMP_DIR: DirectoryPath = BASE_DIR / "temp"
CONFIG_DIR: DirectoryPath = BASE_DIR / "config"

ARCHIVE_DIR: DirectoryPath = DATA_DIR / "archive"
OCR_DIR: DirectoryPath = DATA_DIR / "ocr"
EXTRACTION_DIR: DirectoryPath = DATA_DIR / "extraction"
REVIEW_DIR: DirectoryPath = DATA_DIR / "review"
KNOWLEDGE_DIR: DirectoryPath = DATA_DIR / "knowledge"
RECORDS_DIR: DirectoryPath = KNOWLEDGE_DIR / "records"
PACKAGES_DIR: DirectoryPath = DATA_DIR / "packages"
EXPORTS_DIR: DirectoryPath = DATA_DIR / "exports"
FORMS_DIR: DirectoryPath = DATA_DIR / "forms"
TEMPLATES_DIR: DirectoryPath = DATA_DIR / "templates"
MODELS_DIR: DirectoryPath = DATA_DIR / "models"
VAULT_DIR: DirectoryPath = DATA_DIR / "vault"
AUDIT_DIR: DirectoryPath = DATA_DIR / "audit"
DATABASE_DIR: DirectoryPath = DATA_DIR / "database"
JOBS_DIR: DirectoryPath = TEMP_DIR / "jobs"
UPLOADS_DIR: DirectoryPath = TEMP_DIR / "uploads"
PROCESSING_DIR: DirectoryPath = TEMP_DIR / "processing"

DATABASE_FILE: FilePath = DATABASE_DIR / DATABASE_FILENAME
APP_LOG_FILE: FilePath = LOGS_DIR / "nasmi.log"
AUDIT_LOG_FILE: FilePath = LOGS_DIR / "audit.log"
ERROR_LOG_FILE: FilePath = LOGS_DIR / "errors.log"


def document_archive_path(doc_id: DocumentId) -> DirectoryPath:
    return ARCHIVE_DIR / doc_id


def document_original_path(doc_id: DocumentId) -> DirectoryPath:
    return document_archive_path(doc_id) / "original"


def document_original_file(doc_id: DocumentId, filename: str) -> FilePath:
    return document_original_path(doc_id) / filename


def document_metadata_file(doc_id: DocumentId) -> FilePath:
    return document_archive_path(doc_id) / "metadata.json"


def document_hash_file(doc_id: DocumentId) -> FilePath:
    return document_archive_path(doc_id) / "hash.txt"


def document_ocr_path(doc_id: DocumentId) -> DirectoryPath:
    return OCR_DIR / doc_id


def document_extraction_path(doc_id: DocumentId) -> DirectoryPath:
    return EXTRACTION_DIR / doc_id


def document_review_path(doc_id: DocumentId) -> DirectoryPath:
    return REVIEW_DIR / doc_id


def knowledge_record_path(knowledge_id: KnowledgeId) -> DirectoryPath:
    return RECORDS_DIR / knowledge_id


def package_path(package_id: PackageId) -> DirectoryPath:
    return PACKAGES_DIR / package_id


def package_manifest_file(package_id: PackageId) -> FilePath:
    return package_path(package_id) / "manifest.json"


def package_export_path(package_id: PackageId) -> DirectoryPath:
    return EXPORTS_DIR / package_id


def package_export_file(package_id: PackageId, filename: str) -> FilePath:
    return package_export_path(package_id) / filename


def audit_chain_file(entity_id: EntityId) -> FilePath:
    return AUDIT_DIR / f"{entity_id}.jsonl"


def job_path(job_id: JobId) -> DirectoryPath:
    return JOBS_DIR / job_id


_REQUIRED_DIRS: tuple[DirectoryPath, ...] = (
    DATA_DIR,
    LOGS_DIR,
    TEMP_DIR,
    CONFIG_DIR,
    ARCHIVE_DIR,
    OCR_DIR,
    EXTRACTION_DIR,
    REVIEW_DIR,
    KNOWLEDGE_DIR,
    RECORDS_DIR,
    PACKAGES_DIR,
    EXPORTS_DIR,
    FORMS_DIR,
    TEMPLATES_DIR,
    MODELS_DIR,
    VAULT_DIR,
    AUDIT_DIR,
    DATABASE_DIR,
    JOBS_DIR,
    UPLOADS_DIR,
    PROCESSING_DIR,
)


def ensure_directories() -> None:
    for directory in _REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
