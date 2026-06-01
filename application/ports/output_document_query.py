from __future__ import annotations

from abc import ABC, abstractmethod

from core.types import EntityId
from output.output_document import OutputDocument
from output.output_ids import OutputDocumentId


class OutputDocumentQueryService(ABC):

    @abstractmethod
    def get_by_id(
        self,
        output_document_id: OutputDocumentId,
    ) -> OutputDocument | None:
        """
        Returns the OutputDocument with the given ID,
        or None if not found.
        """

    @abstractmethod
    def list_by_subject(
        self,
        subject_id: EntityId,
    ) -> tuple[OutputDocument, ...]:
        """
        Returns all OutputDocuments belonging to the given subject.
        Returns an empty tuple if none exist.
        """
