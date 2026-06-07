from __future__ import annotations

import threading
from dataclasses import dataclass

from core.paths import (
    DATABASE_FILE,
    PACKAGES_DIR,
    ensure_directories,
)
from infrastructure.container import Container
from infrastructure.db.connection import DatabaseConnection, get_db, init_db
from infrastructure.db.repositories.sqlite_audit_query import SqliteAuditQuery
from infrastructure.db.repositories.sqlite_conflict_repository import (
    SqliteConflictRepository,
)
from infrastructure.db.repositories.sqlite_document_repository import (
    SqliteDocumentRepository,
)
from infrastructure.db.repositories.sqlite_entity_repository import (
    SqliteEntityRepository,
)
from infrastructure.db.repositories.sqlite_output_document_repository import (
    SqliteOutputDocumentRepository,
)
from infrastructure.db.repositories.sqlite_review_repository import (
    SqliteReviewRepository,
)
from infrastructure.db.sqlite_knowledge_query import SqliteKnowledgeQuery
from infrastructure.db.sqlite_profile_query import SqliteProfileQuery
from processing.extraction.extractor_registry import ExtractorRegistry
from processing.extraction.extractors.employment.employment_contract_extractor import (
    EmploymentContractExtractor,
)
from processing.extraction.extractors.employment.payslip_extractor import (
    PayslipExtractor,
)
from processing.extraction.extractors.financial.bank_statement_extractor import (
    BankStatementExtractor,
)
from processing.extraction.extractors.financial.invoice_extractor import (
    InvoiceExtractor,
)
from processing.extraction.extractors.german.id_card_extractor import IdCardExtractor
from processing.extraction.extractors.german.residence_permit_extractor import (
    ResidencePermitExtractor,
)
from processing.extraction.extractors.passport_extractor import PassportExtractor
from processing.ocr.engines.tesseract_ocr_engine import TesseractOcrEngine
from processing.ocr.ocr_engine_registry import OcrEngineRegistry

_db_lock = threading.Lock()
_db_initialised = False


def _ensure_db() -> DatabaseConnection:
    global _db_initialised
    if _db_initialised:
        return get_db()
    with _db_lock:
        if not _db_initialised:
            ensure_directories()
            init_db(DATABASE_FILE)
            _db_initialised = True
    return get_db()


def _get_db() -> DatabaseConnection:
    return _ensure_db()


def _build_extractor_registry() -> ExtractorRegistry:
    registry = ExtractorRegistry()
    registry.register(PassportExtractor())
    registry.register(IdCardExtractor())
    registry.register(ResidencePermitExtractor())
    registry.register(EmploymentContractExtractor())
    registry.register(PayslipExtractor())
    registry.register(BankStatementExtractor())
    registry.register(InvoiceExtractor())
    return registry


_container_lock = threading.Lock()
_container: Container | None = None


def _get_container() -> Container:
    global _container
    if _container is not None:
        return _container
    with _container_lock:
        if _container is None:
            ensure_directories()
            db = _ensure_db()
            ocr_registry = OcrEngineRegistry(default_engine_name="tesseract")
            ocr_registry.register(TesseractOcrEngine())
            extractor_registry = _build_extractor_registry()
            _container = Container(
                base_output_dir=PACKAGES_DIR,
                db=db,
                ocr_engine_registry=ocr_registry,
                extractor_registry=extractor_registry,
            )
    return _container


def get_document_repo() -> SqliteDocumentRepository:
    return SqliteDocumentRepository(_get_db())


def get_entity_repo() -> SqliteEntityRepository:
    return SqliteEntityRepository(_get_db())


def get_review_repo() -> SqliteReviewRepository:
    return SqliteReviewRepository(_get_db())


def get_conflict_repo() -> SqliteConflictRepository:
    return SqliteConflictRepository(_get_db())


def get_output_doc_repo() -> SqliteOutputDocumentRepository:
    return SqliteOutputDocumentRepository(_get_db())


def get_knowledge_query() -> SqliteKnowledgeQuery:
    return SqliteKnowledgeQuery(_get_db())


def get_profile_query() -> SqliteProfileQuery:
    return SqliteProfileQuery(_get_db())


def get_audit_query() -> SqliteAuditQuery:
    return SqliteAuditQuery(_get_db())


@dataclass(frozen=True)
class EntityRow:
    entity_id: str
    display_name: str
    entity_type: str
    status: str


def list_entities() -> tuple[EntityRow, ...]:
    try:
        rows = (
            _get_db()
            .connection.execute(
                "SELECT entity_id, display_name, entity_type, status "
                "FROM entities WHERE status = 'active' ORDER BY display_name"
            )
            .fetchall()
        )
        return tuple(
            EntityRow(
                entity_id=r["entity_id"],
                display_name=r["display_name"],
                entity_type=r["entity_type"],
                status=r["status"],
            )
            for r in rows
        )
    except Exception:
        return ()


@dataclass(frozen=True)
class SystemHealth:
    db_ok: bool
    review_queue_count: int
    knowledge_facts_count: int
    error: str = ""


def get_health() -> SystemHealth:
    try:
        conn = _get_db().connection
        (review_count,) = conn.execute(
            "SELECT COUNT(*) FROM review_cases WHERE status = 'PENDING'"
        ).fetchone()
        (facts_count,) = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE status = 'accepted'"
        ).fetchone()
        return SystemHealth(
            db_ok=True,
            review_queue_count=int(review_count),
            knowledge_facts_count=int(facts_count),
        )
    except Exception as exc:
        return SystemHealth(
            db_ok=False,
            review_queue_count=0,
            knowledge_facts_count=0,
            error=str(exc),
        )
