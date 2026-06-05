from __future__ import annotations

from typing import Protocol

from archive.document import Document, DocumentStatus
from core.types import DocumentId, EntityId


class DocumentRepository(Protocol):

    def save(self, document: Document) -> None: ...

    def get(
        self,
        document_id: DocumentId,
    ) -> Document | None: ...

    def exists(
        self,
        document_id: DocumentId,
    ) -> bool: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[Document, ...]: ...

    def list_by_status(
        self,
        status: DocumentStatus,
    ) -> tuple[Document, ...]: ...

    def list_by_entity_and_status(
        self,
        entity_id: EntityId,
        status: DocumentStatus,
    ) -> tuple[Document, ...]: ...
