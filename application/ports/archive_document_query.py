from __future__ import annotations

from abc import ABC, abstractmethod

from archive.document import Document
from core.types import DocumentId, EntityId


class ArchiveDocumentQueryService(ABC):

    @abstractmethod
    def get_by_id(
        self,
        document_id: DocumentId,
    ) -> Document | None:
        """
        Returns the document with the given ID,
        or None if not found.
        """

    @abstractmethod
    def list_by_subject(
        self,
        subject_id: EntityId,
    ) -> tuple[Document, ...]:
        """
        Returns all documents belonging to the given subject.
        Returns an empty tuple if none exist.
        """
