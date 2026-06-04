from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from application.ports.evidence_query import EvidenceQueryService
from core.filesystem import ensure_directory, write_atomic_text
from core.guards import require
from core.time import utcnow
from knowledge.evidence import Evidence
from output.output_document import OutputDocument
from output.output_format import OutputFormat
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


def _evidence_to_dict(evidence: Evidence) -> dict[str, Any]:
    return {
        "evidence_id": str(evidence.evidence_id),
        "source_id": str(evidence.source_id),
        "entity_id": str(evidence.entity_id),
        "field_name": evidence.field_name,
        "raw_value": evidence.raw_value,
        "extraction_method": evidence.extraction_method,
        "confidence": evidence.confidence,
        "created_at": _serialize_canonical(evidence.created_at),
        "location": {k: _serialize_canonical(v) for k, v in evidence.location.items()},
        "metadata": {k: _serialize_canonical(v) for k, v in evidence.metadata.items()},
    }


class EvidenceReportJsonGenerator:

    def __init__(
        self,
        evidence_query: EvidenceQueryService,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(evidence_query, EvidenceQueryService),
            "evidence_query must implement EvidenceQueryService",
        )
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            bool(str(base_output_dir).strip()),
            "base_output_dir must not be blank",
        )
        self._evidence_query = evidence_query
        self._base_output_dir = base_output_dir

    def generate(self, request: OutputRequest) -> OutputDocument:
        require(
            isinstance(request, OutputRequest),
            "request must be an OutputRequest instance",
        )
        require(
            request.output_type is OutputType.EVIDENCE_REPORT,
            f"EvidenceReportJsonGenerator only handles EVIDENCE_REPORT, "
            f"got: {request.output_type!r}",
        )
        require(
            request.output_format is OutputFormat.JSON,
            f"EvidenceReportJsonGenerator only handles JSON format, "
            f"got: {request.output_format!r}",
        )

        evidence_items: tuple[Evidence, ...] = self._evidence_query.list_evidence(
            request.subject_id,
        )
        require(
            isinstance(evidence_items, tuple),
            "EvidenceQueryService.list_evidence must return a tuple",
        )
        require(
            all(isinstance(e, Evidence) for e in evidence_items),
            "all elements returned by list_evidence must be Evidence instances",
        )

        output_document_id: OutputDocumentId = generate_output_document_id()
        generated_at: datetime = utcnow()

        envelope: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "output_document_id": str(output_document_id),
            "entity_id": str(request.subject_id),
            "exported_at": generated_at.isoformat(),
            "evidence_count": len(evidence_items),
            "evidence": [_evidence_to_dict(e) for e in evidence_items],
        }

        file_path: Path = (
            self._base_output_dir
            / str(request.subject_id)
            / "evidence_report"
            / f"evidence_report_{output_document_id}.json"
        )

        ensure_directory(file_path.parent)
        write_atomic_text(
            file_path,
            json.dumps(envelope, ensure_ascii=False, indent=2),
        )

        return OutputDocument(
            output_document_id=output_document_id,
            subject_id=request.subject_id,
            output_type=OutputType.EVIDENCE_REPORT,
            output_format=OutputFormat.JSON,
            generated_at=generated_at,
            file_path=file_path,
        )
