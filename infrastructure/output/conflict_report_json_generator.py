from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from application.ports.conflict_query import ConflictQueryService
from core.filesystem import ensure_directory, write_atomic_text
from core.guards import require
from core.time import utcnow
from knowledge.conflict import Conflict
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_generator import OutputGenerator
from output.output_ids import OutputDocumentId, generate_output_document_id
from output.output_request import OutputRequest
from output.output_type import OutputType

_SCHEMA_VERSION: int = 1


def _serialize_canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _conflict_to_dict(conflict: Conflict) -> dict[str, Any]:
    return {
        "conflict_id": str(conflict.conflict_id),
        "entity_id": str(conflict.entity_id),
        "field_name": conflict.field_name,
        "fact_ids": [str(fid) for fid in conflict.fact_ids],
        "status": str(conflict.status),
        "created_at": _serialize_canonical(conflict.created_at),
        "resolved_fact_id": (
            str(conflict.resolved_fact_id)
            if conflict.resolved_fact_id is not None
            else None
        ),
        "resolution_note": conflict.resolution_note,
        "resolved_by": conflict.resolved_by,
        "resolved_at": (
            _serialize_canonical(conflict.resolved_at)
            if conflict.resolved_at is not None
            else None
        ),
    }


class ConflictReportJsonGenerator(OutputGenerator):

    def __init__(
        self,
        conflict_query: ConflictQueryService,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(conflict_query, ConflictQueryService),
            "conflict_query must implement ConflictQueryService",
        )
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            bool(str(base_output_dir).strip()),
            "base_output_dir must not be blank",
        )
        self._conflict_query = conflict_query
        self._base_output_dir = base_output_dir

    def generate(self, request: OutputRequest) -> OutputDocument:
        require(
            isinstance(request, OutputRequest),
            "request must be an OutputRequest instance",
        )
        require(
            request.output_type is OutputType.CONFLICT_REPORT,
            f"ConflictReportJsonGenerator only handles CONFLICT_REPORT, "
            f"got: {request.output_type!r}",
        )
        require(
            request.output_format is OutputFormat.JSON,
            f"ConflictReportJsonGenerator only handles JSON format, "
            f"got: {request.output_format!r}",
        )

        conflict_items: tuple[Conflict, ...] = self._conflict_query.list_conflicts(
            request.subject_id,
        )
        require(
            isinstance(conflict_items, tuple),
            "ConflictQueryService.list_conflicts must return a tuple",
        )
        require(
            all(isinstance(c, Conflict) for c in conflict_items),
            "all elements returned by list_conflicts must be Conflict instances",
        )

        output_document_id: OutputDocumentId = generate_output_document_id()
        generated_at: datetime = utcnow()

        envelope: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "output_document_id": str(output_document_id),
            "entity_id": str(request.subject_id),
            "exported_at": generated_at.isoformat(),
            "conflict_count": len(conflict_items),
            "open_count": sum(1 for c in conflict_items if c.is_open),
            "terminal_count": sum(1 for c in conflict_items if c.is_terminal),
            "conflicts": [_conflict_to_dict(c) for c in conflict_items],
        }

        file_path: Path = (
            self._base_output_dir
            / str(request.subject_id)
            / "conflict_report"
            / f"conflict_report_{output_document_id}.json"
        )

        ensure_directory(file_path.parent)
        write_atomic_text(
            file_path,
            json.dumps(envelope, ensure_ascii=False, indent=2),
        )

        return OutputDocument(
            output_document_id=output_document_id,
            subject_id=request.subject_id,
            output_type=OutputType.CONFLICT_REPORT,
            output_format=OutputFormat.JSON,
            generated_at=generated_at,
            file_path=file_path,
        )
