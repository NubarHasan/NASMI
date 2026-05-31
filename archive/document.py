from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from core.exceptions import StateError
from core.guards import require
from core.hashing import hash_file
from core.identifiers import generate_document_id, is_valid_entity_id
from core.time import parse_timestamp, utcnow_iso
from core.types import DocumentId


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.PENDING: frozenset(
        {DocumentStatus.PROCESSING, DocumentStatus.FAILED}
    ),
    DocumentStatus.PROCESSING: frozenset(
        {DocumentStatus.PROCESSED, DocumentStatus.FAILED}
    ),
    DocumentStatus.PROCESSED: frozenset(),
    DocumentStatus.FAILED: frozenset(),
}


class DocTypeRegistry:
    _types: dict[str, str] = {}

    _BUILT_IN: tuple[str, ...] = (
        "passport",
        "id_card",
        "residence_permit",
        "insurance",
        "bank_statement",
        "contract",
        "invoice",
        "certificate",
        "other",
    )

    @classmethod
    def _bootstrap(cls) -> None:
        for t in cls._BUILT_IN:
            cls._types[t] = t

    @classmethod
    def register(cls, doc_type: str) -> None:
        require(
            isinstance(doc_type, str) and bool(doc_type.strip()),
            "doc_type must be a non-empty string",
        )
        cls._types[doc_type.strip().lower()] = doc_type.strip().lower()

    @classmethod
    def is_valid(cls, doc_type: object) -> bool:
        if not isinstance(doc_type, str):
            return False
        return doc_type.strip().lower() in cls._types

    @classmethod
    def all(cls) -> list[str]:
        return sorted(cls._types.keys())


DocTypeRegistry._bootstrap()


@dataclass
class Document:
    document_id: DocumentId
    entity_id: str
    doc_type: str
    file_hash: str
    file_path: str
    language: str
    status: DocumentStatus
    created_at: str

    issued_at: str | None = field(default=None)
    expires_at: str | None = field(default=None)
    metadata: dict[str, Any] = field(default_factory=dict)

    def _transition(self, target: DocumentStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise StateError(
                f"invalid document transition: {self.status} -> {target} "
                f"(document_id={self.document_id!r})"
            )
        self.status = target

    def start_processing(self) -> None:
        self._transition(DocumentStatus.PROCESSING)

    def mark_processed(self) -> None:
        self._transition(DocumentStatus.PROCESSED)

    def mark_failed(self) -> None:
        self._transition(DocumentStatus.FAILED)

    @property
    def is_terminal(self) -> bool:
        return self.status in {DocumentStatus.PROCESSED, DocumentStatus.FAILED}

    def is_expired(self, reference_date: str) -> bool:
        if self.expires_at is None:
            return False
        return parse_timestamp(reference_date) >= parse_timestamp(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "entity_id": self.entity_id,
            "doc_type": self.doc_type,
            "file_hash": self.file_hash,
            "file_path": self.file_path,
            "language": self.language,
            "status": str(self.status),
            "created_at": self.created_at,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        return cls(
            document_id=DocumentId(data["document_id"]),
            entity_id=data["entity_id"],
            doc_type=data["doc_type"],
            file_hash=data["file_hash"],
            file_path=data["file_path"],
            language=data["language"],
            status=DocumentStatus(data["status"]),
            created_at=data["created_at"],
            issued_at=data.get("issued_at"),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        entity_id: str,
        doc_type: str,
        file_path: str | Path,
        language: str,
        issued_at: str | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        require(DocTypeRegistry.is_valid(doc_type), f"unknown doc_type: {doc_type!r}")
        require(
            isinstance(language, str) and bool(language.strip()),
            "language must be a non-empty string",
        )

        path = Path(file_path)
        require(path.is_file(), f"file not found: {path}")

        return cls(
            document_id=generate_document_id(),
            entity_id=entity_id,
            doc_type=doc_type,
            file_hash=hash_file(path),
            file_path=str(path),
            language=language,
            status=DocumentStatus.PENDING,
            created_at=utcnow_iso(),
            issued_at=issued_at,
            expires_at=expires_at,
            metadata=dict(metadata) if metadata else {},
        )
