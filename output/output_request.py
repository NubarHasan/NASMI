from dataclasses import dataclass
from datetime import datetime

from core.entity import EntityId
from core.validation import is_valid_entity_id, require

from output.output_format import OutputFormat
from output.output_type import OutputType


@dataclass(frozen=True)
class OutputRequest:
    subject_id: EntityId
    output_type: OutputType
    output_format: OutputFormat
    requested_at: datetime

    def __post_init__(self) -> None:
        require(
            is_valid_entity_id(self.subject_id),
            "OutputRequest.subject_id must be a valid EntityId",
        )
        require(
            isinstance(self.output_type, OutputType),
            "OutputRequest.output_type must be an OutputType",
        )
        require(
            isinstance(self.output_format, OutputFormat),
            "OutputRequest.output_format must be an OutputFormat",
        )
        require(
            isinstance(self.requested_at, datetime),
            "OutputRequest.requested_at must be a datetime",
        )
