from __future__ import annotations

from typing import Protocol

from archive.document_status import DocumentStatus

from archive.document import Document
from core.types import DocumentId, ExternalRef


class DocumentRepository(Protocol):

    def save(self, document: Document) -> None: ...

    def get(self, document_id: DocumentId) -> Document | None: ...

    def exists(self, document_id: DocumentId) -> bool: ...

    def exists_by_external_ref(
        self,
        external_ref: ExternalRef,
    ) -> bool: ...

    def list_by_status(
        self,
        status: DocumentStatus,
    ) -> tuple[Document, ...]: ...

    def mark_processed(
        self,
        document_id: DocumentId,
    ) -> None: ...

    def mark_failed(
        self,
        document_id: DocumentId,
    ) -> None: ...
