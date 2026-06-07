from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.identifiers import generate_entity_id
from core.paths import DATABASE_FILE, PACKAGES_DIR, ensure_directories
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
from processing.extraction.extractors.universal_document_extractor import (
    UniversalDocumentExtractor,
)
from processing.ocr.engines.tesseract_ocr_engine import TesseractOcrEngine
from processing.ocr.ocr_engine_registry import OcrEngineRegistry

_db_lock = threading.Lock()
_db_initialised = False
_container_lock = threading.Lock()
_container: Container | None = None


@dataclass(frozen=True)
class EntityRow:
    entity_id: str
    display_name: str
    entity_type: str
    status: str


@dataclass(frozen=True)
class SystemHealth:
    db_ok: bool
    active_entity_id: str | None
    active_entity_name: str | None
    entities_count: int
    documents_count: int
    sources_count: int
    extracted_facts_count: int
    accepted_facts_count: int
    pending_review_count: int
    accepted_review_count: int
    rejected_review_count: int
    profiles_count: int
    noise_count: int
    outputs_count: int
    audit_count: int
    next_step: str
    pipeline_stage: str
    error: str = ""


@dataclass(frozen=True)
class ProfileStatus:
    entity_exists: bool
    profile_exists: bool
    accepted_facts_count: int
    pending_review_count: int
    documents_count: int
    next_step: str


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
    registry.register(UniversalDocumentExtractor())
    return registry


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


def _count(conn: Any, table: str, where: str = "", params: tuple[Any, ...] = ()) -> int:
    query = f"SELECT COUNT(*) FROM {table}"
    if where:
        query += f" WHERE {where}"
    row = conn.execute(query, params).fetchone()
    return int(row[0]) if row else 0


def _table_exists(conn: Any, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _profile_fields_count(conn: Any, entity_id: str | None = None) -> int:
    if not _table_exists(conn, "profile_fields"):
        return 0

    if entity_id:
        return _count(
            conn,
            "profile_fields",
            "entity_id = ?",
            (entity_id,),
        )

    row = conn.execute("""
        SELECT COUNT(DISTINCT entity_id)
        FROM profile_fields
        """).fetchone()
    return int(row[0]) if row else 0


def _legacy_profiles_count(conn: Any, entity_id: str | None = None) -> int:
    if not _table_exists(conn, "profiles"):
        return 0

    if entity_id:
        return _count(
            conn,
            "profiles",
            "entity_id = ?",
            (entity_id,),
        )

    return _count(conn, "profiles")


def _trusted_profiles_count(conn: Any) -> int:
    legacy_count = _legacy_profiles_count(conn)
    profile_fields_entities_count = _profile_fields_count(conn)

    if legacy_count == 0:
        return profile_fields_entities_count

    if profile_fields_entities_count == 0:
        return legacy_count

    if not _table_exists(conn, "profile_fields") or not _table_exists(conn, "profiles"):
        return legacy_count + profile_fields_entities_count

    rows = conn.execute("""
        SELECT entity_id FROM profiles
        UNION
        SELECT entity_id FROM profile_fields
        """).fetchall()

    return len(rows)


def _trusted_profile_exists(conn: Any, entity_id: str | None) -> bool:
    if not entity_id:
        return False

    return (
        _legacy_profiles_count(conn, entity_id) > 0
        or _profile_fields_count(conn, entity_id) > 0
    )


def list_entities() -> tuple[EntityRow, ...]:
    try:
        rows = _get_db().connection.execute("""
                SELECT entity_id, display_name, entity_type, status
                FROM entities
                WHERE status = 'active'
                ORDER BY created_at DESC, display_name
                """).fetchall()
        return tuple(
            EntityRow(
                entity_id=str(row["entity_id"]),
                display_name=str(row["display_name"]),
                entity_type=str(row["entity_type"]),
                status=str(row["status"]),
            )
            for row in rows
        )
    except Exception:
        return ()


def create_entity(
    display_name: str,
    entity_type: str = "person",
    primary_language: str = "en",
) -> EntityRow:
    name = display_name.strip()
    if not name:
        raise ValueError("Display name is required.")

    entity_id = str(generate_entity_id())
    now = datetime.now(UTC).isoformat()

    conn = _get_db().connection
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
            entity_id,
            entity_type,
            name,
            "active",
            now,
            now,
            primary_language,
            None,
            "{}",
        ),
    )
    conn.commit()

    return EntityRow(
        entity_id=entity_id,
        display_name=name,
        entity_type=entity_type,
        status="active",
    )


def get_entity(entity_id: str | None) -> EntityRow | None:
    if not entity_id:
        return None
    try:
        row = (
            _get_db()
            .connection.execute(
                """
                SELECT entity_id, display_name, entity_type, status
                FROM entities
                WHERE entity_id = ?
                LIMIT 1
                """,
                (entity_id,),
            )
            .fetchone()
        )
        if row is None:
            return None
        return EntityRow(
            entity_id=str(row["entity_id"]),
            display_name=str(row["display_name"]),
            entity_type=str(row["entity_type"]),
            status=str(row["status"]),
        )
    except Exception:
        return None


def get_entity_display_name(entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    try:
        row = (
            _get_db()
            .connection.execute(
                "SELECT display_name FROM entities WHERE entity_id = ? LIMIT 1",
                (entity_id,),
            )
            .fetchone()
        )
        if row is None:
            return None
        return str(row["display_name"])
    except Exception:
        return None


def get_first_active_entity_id() -> str | None:
    entities = list_entities()
    if not entities:
        return None
    return entities[0].entity_id


def resolve_active_entity_id(current_entity_id: str | None = None) -> str | None:
    entities = list_entities()
    if not entities:
        return None
    ids = {entity.entity_id for entity in entities}
    if current_entity_id in ids:
        return current_entity_id
    return entities[0].entity_id


def _compute_next_step(
    entities_count: int,
    documents_count: int,
    extracted_facts_count: int,
    pending_review_count: int,
    accepted_facts_count: int,
    profiles_count: int,
    outputs_count: int,
) -> tuple[str, str]:
    if entities_count == 0:
        return (
            "Entity Start",
            "Create or select an active entity before uploading documents.",
        )
    if documents_count == 0:
        return (
            "Document Intake",
            "Upload the first source document for the active entity.",
        )
    if extracted_facts_count == 0:
        return "Extraction", "Process uploaded documents to extract candidate facts."
    if pending_review_count > 0 and accepted_facts_count == 0:
        return "Human Review", "Open Review and accept the correct extracted facts."
    if accepted_facts_count > 0 and profiles_count == 0:
        return "Profile Build", "Build the trusted profile from accepted facts."
    if profiles_count > 0 and outputs_count == 0:
        return (
            "Forms and Output",
            "Use the trusted profile to fill forms or generate outputs.",
        )
    return (
        "Operational",
        "Pipeline is ready. Continue with documents, review, forms, or advisory.",
    )


def get_health(active_entity_id: str | None = None) -> SystemHealth:
    try:
        conn = _get_db().connection
        resolved_entity_id = resolve_active_entity_id(active_entity_id)
        active_entity_name = get_entity_display_name(resolved_entity_id)

        entities_count = _count(conn, "entities", "status = 'active'")
        documents_count = _count(conn, "documents")
        sources_count = _count(conn, "sources")
        extracted_facts_count = _count(conn, "facts")
        accepted_facts_count = _count(conn, "facts", "status = 'accepted'")
        pending_review_count = _count(conn, "review_cases", "status = 'PENDING'")
        accepted_review_count = _count(conn, "review_cases", "status = 'ACCEPTED'")
        rejected_review_count = _count(conn, "review_cases", "status = 'REJECTED'")
        profiles_count = _trusted_profiles_count(conn)
        noise_count = _count(conn, "noise_items")
        outputs_count = _count(conn, "output_documents")
        audit_count = _count(conn, "audit_entries")

        pipeline_stage, next_step = _compute_next_step(
            entities_count=entities_count,
            documents_count=documents_count,
            extracted_facts_count=extracted_facts_count,
            pending_review_count=pending_review_count,
            accepted_facts_count=accepted_facts_count,
            profiles_count=profiles_count,
            outputs_count=outputs_count,
        )

        return SystemHealth(
            db_ok=True,
            active_entity_id=resolved_entity_id,
            active_entity_name=active_entity_name,
            entities_count=entities_count,
            documents_count=documents_count,
            sources_count=sources_count,
            extracted_facts_count=extracted_facts_count,
            accepted_facts_count=accepted_facts_count,
            pending_review_count=pending_review_count,
            accepted_review_count=accepted_review_count,
            rejected_review_count=rejected_review_count,
            profiles_count=profiles_count,
            noise_count=noise_count,
            outputs_count=outputs_count,
            audit_count=audit_count,
            next_step=next_step,
            pipeline_stage=pipeline_stage,
        )
    except Exception as exc:
        return SystemHealth(
            db_ok=False,
            active_entity_id=None,
            active_entity_name=None,
            entities_count=0,
            documents_count=0,
            sources_count=0,
            extracted_facts_count=0,
            accepted_facts_count=0,
            pending_review_count=0,
            accepted_review_count=0,
            rejected_review_count=0,
            profiles_count=0,
            noise_count=0,
            outputs_count=0,
            audit_count=0,
            next_step="Database is not ready.",
            pipeline_stage="Offline",
            error=str(exc),
        )


def get_profile_status(entity_id: str | None) -> ProfileStatus:
    if not entity_id:
        return ProfileStatus(
            entity_exists=False,
            profile_exists=False,
            accepted_facts_count=0,
            pending_review_count=0,
            documents_count=0,
            next_step="Create an entity first.",
        )

    conn = _get_db().connection

    entity_exists = (
        conn.execute(
            "SELECT 1 FROM entities WHERE entity_id = ? LIMIT 1",
            (entity_id,),
        ).fetchone()
        is not None
    )

    profile_exists = _trusted_profile_exists(conn, entity_id)

    accepted_facts_count = _count(
        conn,
        "facts",
        "entity_id = ? AND status = 'accepted'",
        (entity_id,),
    )
    pending_review_count = _count(
        conn,
        "review_cases",
        "entity_id = ? AND status = 'PENDING'",
        (entity_id,),
    )
    documents_count = _count(
        conn,
        "documents",
        "entity_id = ?",
        (entity_id,),
    )

    if not entity_exists:
        next_step = "Create an entity first."
    elif documents_count == 0:
        next_step = "Upload documents for this entity."
    elif pending_review_count > 0:
        next_step = "Review pending extracted facts."
    elif accepted_facts_count == 0:
        next_step = "Accept facts before building a trusted profile."
    elif not profile_exists:
        next_step = "Build the profile from accepted facts."
    else:
        next_step = "Profile is ready."

    return ProfileStatus(
        entity_exists=entity_exists,
        profile_exists=profile_exists,
        accepted_facts_count=accepted_facts_count,
        pending_review_count=pending_review_count,
        documents_count=documents_count,
        next_step=next_step,
    )


def read_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None
