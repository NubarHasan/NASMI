from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from application.ports.profile_query import ProfileQueryService
from core.filesystem import ensure_directory, write_atomic_text
from core.guards import require
from core.time import utcnow
from knowledge.profile import Profile, ProfileField
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


def _serialize_profile_field(f: ProfileField) -> dict[str, Any]:
    return {
        "field_name": f.field_name,
        "value": _serialize_canonical(f.value),
        "display_value": f.display_value,
        "confidence": f.confidence,
        "fact_id": str(f.fact_id),
        "sourced_at": _serialize_canonical(f.sourced_at),
    }


def _serialize_profile(profile: Profile) -> dict[str, Any]:
    return {
        "profile_id": str(profile.profile_id),
        "entity_type": profile.entity_type,
        "display_name": profile.display_name,
        "completeness": profile.completeness,
        "computed_at": _serialize_canonical(profile.computed_at),
        "field_count": len(profile.fields),
        "fields": [_serialize_profile_field(f) for f in profile.fields.values()],
        "metadata": {k: _serialize_canonical(v) for k, v in profile.metadata.items()},
    }


class ProfileReportJsonGenerator:

    def __init__(
        self,
        profile_query: ProfileQueryService,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(profile_query, ProfileQueryService),
            "profile_query must implement ProfileQueryService",
        )
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            bool(str(base_output_dir).strip()),
            "base_output_dir must not be blank",
        )
        self._profile_query = profile_query
        self._base_output_dir = base_output_dir

    def generate(
        self,
        request: OutputRequest,
    ) -> OutputDocument:
        require(
            isinstance(request, OutputRequest),
            "request must be an OutputRequest",
        )
        require(
            request.output_type is OutputType.PROFILE_REPORT,
            f"expected PROFILE_REPORT, got {request.output_type!r}",
        )
        require(
            request.output_format is OutputFormat.JSON,
            f"expected JSON, got {request.output_format!r}",
        )

        profile = self._profile_query.get_profile(request.subject_id)
        require(
            profile is not None,
            f"no profile found for entity {request.subject_id!r}",
        )
        assert profile is not None

        output_document_id: OutputDocumentId = generate_output_document_id()
        generated_at: datetime = utcnow()

        envelope: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "output_document_id": str(output_document_id),
            "entity_id": str(request.subject_id),
            "exported_at": generated_at.isoformat(),
            "profile": _serialize_profile(profile),
        }

        file_path: Path = (
            self._base_output_dir
            / str(request.subject_id)
            / "profile_report"
            / f"profile_report_{output_document_id}.json"
        )

        ensure_directory(file_path.parent)
        write_atomic_text(
            file_path,
            json.dumps(envelope, ensure_ascii=False, indent=2),
        )

        return OutputDocument(
            output_document_id=output_document_id,
            subject_id=request.subject_id,
            output_type=OutputType.PROFILE_REPORT,
            output_format=OutputFormat.JSON,
            generated_at=generated_at,
            file_path=file_path,
        )
