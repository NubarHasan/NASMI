from __future__ import annotations

from typing import Protocol

from core.types import EntityId
from output.output_document import OutputDocument
from output.output_ids import OutputDocumentId
from output.output_type import OutputType


class OutputDocumentRepository(Protocol):

    def save(self, document: OutputDocument) -> None: ...

    def get(
        self,
        output_document_id: OutputDocumentId,
    ) -> OutputDocument | None: ...

    def exists(
        self,
        output_document_id: OutputDocumentId,
    ) -> bool: ...

    def list_by_entity(
        self,
        entity_id: EntityId,
    ) -> tuple[OutputDocument, ...]: ...

    def list_by_entity_and_type(
        self,
        entity_id: EntityId,
        output_type: OutputType,
    ) -> tuple[OutputDocument, ...]: ...

    def get_latest_by_entity_and_type(
        self,
        entity_id: EntityId,
        output_type: OutputType,
    ) -> OutputDocument | None: ...
