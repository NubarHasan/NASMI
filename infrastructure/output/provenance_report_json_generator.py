from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from application.ports.provenance_query import ProvenanceQueryService
from core.filesystem import ensure_directory, write_atomic_text
from core.guards import require
from core.time import utcnow
from knowledge.provenance import Provenance, ProvenanceStep
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


def _step_to_dict(step: ProvenanceStep) -> dict[str, Any]:
    return {
        "step_order": step.step_order,
        "action": step.action,
        "actor": step.actor,
        "occurred_at": _serialize_canonical(step.occurred_at),
        "evidence_id": str(step.evidence_id) if step.evidence_id is not None else None,
        "note": step.note,
    }


def _provenance_to_dict(provenance: Provenance) -> dict[str, Any]:
    return {
        "provenance_id": str(provenance.provenance_id),
        "fact_id": str(provenance.fact_id),
        "entity_id": str(provenance.entity_id),
        "summary": provenance.summary,
        "created_at": _serialize_canonical(provenance.created_at),
        "step_count": len(provenance.decision_chain),
        "decision_chain": [_step_to_dict(step) for step in provenance.decision_chain],
    }


class ProvenanceReportJsonGenerator:

    def __init__(
        self,
        provenance_query: ProvenanceQueryService,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(provenance_query, ProvenanceQueryService),
            "provenance_query must implement ProvenanceQueryService",
        )
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            bool(str(base_output_dir).strip()),
            "base_output_dir must not be blank",
        )
        self._provenance_query = provenance_query
        self._base_output_dir = base_output_dir

    def generate(self, request: OutputRequest) -> OutputDocument:
        require(
            isinstance(request, OutputRequest),
            "request must be an OutputRequest instance",
        )
        require(
            request.output_type is OutputType.PROVENANCE_REPORT,
            f"ProvenanceReportJsonGenerator only handles PROVENANCE_REPORT, "
            f"got: {request.output_type!r}",
        )
        require(
            request.output_format is OutputFormat.JSON,
            f"ProvenanceReportJsonGenerator only handles JSON format, "
            f"got: {request.output_format!r}",
        )

        provenance_items: tuple[Provenance, ...] = (
            self._provenance_query.list_provenance(request.subject_id)
        )
        require(
            isinstance(provenance_items, tuple),
            "ProvenanceQueryService.list_provenance must return a tuple",
        )
        require(
            all(isinstance(p, Provenance) for p in provenance_items),
            "all elements returned by list_provenance must be Provenance instances",
        )

        output_document_id: OutputDocumentId = generate_output_document_id()
        exported_at: datetime = utcnow()

        envelope: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "output_document_id": str(output_document_id),
            "exported_at": exported_at.isoformat(),
            "entity_id": str(request.subject_id),
            "provenance_count": len(provenance_items),
            "provenance_records": [_provenance_to_dict(p) for p in provenance_items],
        }

        output_dir: Path = (
            self._base_output_dir / str(request.subject_id) / "provenance_report"
        )
        ensure_directory(output_dir)

        filename = (
            f"provenance_report"
            f"_{output_document_id}"
            f"_{exported_at:%Y%m%dT%H%M%S}.json"
        )
        output_path: Path = output_dir / filename

        write_atomic_text(
            output_path,
            json.dumps(envelope, ensure_ascii=False, indent=2),
        )

        return OutputDocument(
            output_document_id=output_document_id,
            output_type=OutputType.PROVENANCE_REPORT,
            output_format=OutputFormat.JSON,
            subject_id=request.subject_id,
            file_path=output_path,
            generated_at=exported_at,
        )
