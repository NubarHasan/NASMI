from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from application.ports.knowledge_query import KnowledgeQueryService
from core.filesystem import ensure_directory, write_atomic_text
from core.guards import require
from core.time import utcnow
from knowledge.fact import CanonicalValue, Fact
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId, generate_output_document_id
from output.output_request import OutputRequest
from output.output_type import OutputType

_SCHEMA_VERSION: int = 1


def _serialize_canonical(value: CanonicalValue) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _fact_to_dict(fact: Fact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "field_name": fact.field_name,
        "value": _serialize_canonical(fact.canonical_value),
        "display_value": fact.display_value,
        "value_type": fact.value_type,
        "confidence": fact.confidence,
        "source_stage": fact.source_stage,
        "created_at": _serialize_canonical(fact.created_at),
        "accepted_at": _serialize_canonical(fact.accepted_at),
        "accepted_by": fact.accepted_by,
    }


class FactExportJsonGenerator:

    def __init__(
        self,
        knowledge_query: KnowledgeQueryService,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(knowledge_query, KnowledgeQueryService),
            "knowledge_query must implement KnowledgeQueryService",
        )
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            bool(str(base_output_dir).strip()),
            "base_output_dir must not be blank",
        )
        self._knowledge_query = knowledge_query
        self._base_output_dir = base_output_dir

    def generate(self, request: OutputRequest) -> OutputDocument:
        require(
            isinstance(request, OutputRequest),
            "request must be an OutputRequest instance",
        )
        require(
            request.output_type is OutputType.FACT_EXPORT,
            f"FactExportJsonGenerator only handles FACT_EXPORT, "
            f"got: {request.output_type!r}",
        )
        require(
            request.output_format is OutputFormat.JSON,
            f"FactExportJsonGenerator only handles JSON format, "
            f"got: {request.output_format!r}",
        )

        facts: tuple[Fact, ...] = self._knowledge_query.list_accepted_facts(
            request.subject_id,
        )
        require(
            isinstance(facts, tuple),
            "KnowledgeQueryService.list_accepted_facts must return a tuple",
        )
        require(
            all(isinstance(f, Fact) for f in facts),
            "all elements returned by list_accepted_facts must be Fact instances",
        )

        output_document_id: OutputDocumentId = generate_output_document_id()
        generated_at: datetime = utcnow()

        envelope: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "output_document_id": str(output_document_id),
            "entity_id": str(request.subject_id),
            "exported_at": generated_at.isoformat(),
            "fact_count": len(facts),
            "facts": [_fact_to_dict(f) for f in facts],
        }

        file_path: Path = (
            self._base_output_dir
            / str(request.subject_id)
            / "fact_export"
            / f"fact_export_{output_document_id}.json"
        )

        ensure_directory(file_path.parent)
        write_atomic_text(
            file_path,
            json.dumps(envelope, ensure_ascii=False, indent=2),
        )

        return OutputDocument(
            output_document_id=output_document_id,
            subject_id=request.subject_id,
            output_type=OutputType.FACT_EXPORT,
            output_format=OutputFormat.JSON,
            generated_at=generated_at,
            file_path=file_path,
        )
