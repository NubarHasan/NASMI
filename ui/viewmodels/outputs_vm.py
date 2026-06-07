from __future__ import annotations

from core.types import EntityId
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId
from output.output_template import OUTPUT_TEMPLATES
from output.output_type import OutputType
from pipeline.job import Job, JobPriority, JobType
from ui.services.api_client import _get_container, _get_db
from ui.viewmodels.output_models import GenerateResult, OutputDetail, OutputSummary


def _active_entity_id() -> str | None:
    try:
        from ui.state import session_manager as sm
        from ui.state.session_keys import SessionKeys

        val = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
        return str(val) if val is not None else None
    except Exception:
        return None


_SUPPORTED_TYPES: tuple[OutputType, ...] = tuple(
    sorted(OUTPUT_TEMPLATES.keys(), key=lambda t: t.value)
)


def _row_to_summary(row: object) -> OutputSummary:
    from pathlib import Path

    output_type = OutputType(row["output_type"])  # type: ignore[index]
    output_format = OutputFormat(row["output_format"])  # type: ignore[index]
    file_path = Path(row["file_path"])  # type: ignore[index]
    template = OUTPUT_TEMPLATES.get(output_type)
    label = template.label if template else str(output_type.value)
    return OutputSummary(
        output_id=OutputDocumentId(row["output_document_id"]),  # type: ignore[index]
        label=label,
        output_type=output_type,
        output_format=output_format,
        succeeded=file_path.exists(),
    )


def _load_outputs(entity_id: str) -> tuple[OutputSummary, ...]:
    try:
        rows = (
            _get_db()
            .connection.execute(
                "SELECT output_document_id, subject_id, output_type, output_format, "
                "file_path FROM output_documents WHERE subject_id = ? "
                "ORDER BY generated_at DESC",
                (entity_id,),
            )
            .fetchall()
        )
        return tuple(_row_to_summary(r) for r in rows)
    except Exception:
        return ()


class OutputsVM:

    def initial_outputs(self) -> tuple[OutputSummary, ...]:
        entity_id = _active_entity_id()
        if entity_id is None:
            return ()
        return _load_outputs(entity_id)

    def supported_types(self) -> tuple[OutputType, ...]:
        return _SUPPORTED_TYPES

    def label_for(self, output_type: OutputType) -> str:
        template = OUTPUT_TEMPLATES.get(output_type)
        return template.label if template else output_type.value

    def description_for(self, output_type: OutputType) -> str:
        template = OUTPUT_TEMPLATES.get(output_type)
        return template.description if template else ""

    def get_detail(
        self,
        output_id: OutputDocumentId,
        outputs: tuple[OutputSummary, ...],
    ) -> OutputDetail | None:
        for summary in outputs:
            if summary.output_id == output_id:
                file_path = (
                    f"outputs/{summary.output_id}.json" if summary.succeeded else ""
                )
                return OutputDetail(
                    output_id=summary.output_id,
                    label=summary.label,
                    output_type=summary.output_type,
                    output_format=summary.output_format,
                    succeeded=summary.succeeded,
                    file_path=file_path,
                )
        return None

    def generate(
        self,
        output_type: OutputType,
        current_outputs: tuple[OutputSummary, ...],
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> tuple[GenerateResult, tuple[OutputSummary, ...]]:
        if output_type not in _SUPPORTED_TYPES:
            return (
                GenerateResult(
                    success=False,
                    error=f"Output type '{output_type}' is not supported.",
                ),
                current_outputs,
            )

        entity_id = _active_entity_id()
        if entity_id is None:
            return (
                GenerateResult(success=False, error="No active entity selected."),
                current_outputs,
            )

        try:
            job = Job.create(
                job_type=JobType.OUTPUT_BUILD,
                payload={
                    "entity_id": entity_id,
                    "output_type": output_type.value,
                    "output_format": output_format.value,
                },
                priority=JobPriority.NORMAL,
            )
            _get_container().output_build_handler.handle(job)

            refreshed = _load_outputs(entity_id)
            new_entry = next((s for s in refreshed if s not in current_outputs), None)
            if new_entry:
                detail = self.get_detail(new_entry.output_id, refreshed)
                return GenerateResult(success=True, detail=detail), refreshed

            return GenerateResult(success=True), refreshed

        except Exception as exc:
            return (
                GenerateResult(success=False, error=str(exc)),
                current_outputs,
            )
