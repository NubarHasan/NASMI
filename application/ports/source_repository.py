from __future__ import annotations

from typing import Protocol

from archive.source import Source
from core.types import DocumentId, EntityId, SourceId


class SourceRepository(Protocol):

    def save(self, source: Source) -> None: ...

    def get(self, source_id: SourceId) -> Source | None: ...

    def exists(self, source_id: SourceId) -> bool: ...

    def list_by_entity(self, entity_id: EntityId) -> tuple[Source, ...]: ...

    def list_by_document(self, document_id: DocumentId) -> tuple[Source, ...]: ...
