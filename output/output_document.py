from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.guards import require
from core.identifiers import is_valid_entity_id
from core.types import EntityId
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId, is_valid_output_document_id
from output.output_type import OutputType


@dataclass(frozen=True)
class OutputDocument:
    output_document_id: OutputDocumentId
    subject_id: EntityId
    output_type: OutputType
    output_format: OutputFormat
    generated_at: datetime
    file_path: Path

    def __post_init__(self) -> None:
        require(
            is_valid_output_document_id(self.output_document_id),
            "output_document_id is not valid",
        )
        require(
            is_valid_entity_id(self.subject_id),
            "subject_id is not valid",
        )
        require(
            isinstance(self.generated_at, datetime),
            "generated_at must be a datetime instance",
        )
        require(
            isinstance(self.file_path, Path),
            "file_path must be a Path instance",
        )
        require(
            bool(str(self.file_path).strip()),
            "file_path must not be blank",
        )
