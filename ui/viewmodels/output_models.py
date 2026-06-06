from __future__ import annotations

from dataclasses import dataclass

from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId
from output.output_type import OutputType


@dataclass(frozen=True)
class OutputSummary:
    output_id: OutputDocumentId
    label: str
    output_type: OutputType
    output_format: OutputFormat
    succeeded: bool


@dataclass(frozen=True)
class OutputDetail:
    output_id: OutputDocumentId
    label: str
    output_type: OutputType
    output_format: OutputFormat
    succeeded: bool
    file_path: str


@dataclass(frozen=True)
class GenerateResult:
    success: bool
    detail: OutputDetail | None = None
    error: str = ""
