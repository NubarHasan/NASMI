from __future__ import annotations

from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId, generate_output_document_id
from output.output_template import OUTPUT_TEMPLATES
from output.output_type import OutputType
from ui.viewmodels.output_models import GenerateResult, OutputDetail, OutputSummary

_SUPPORTED_TYPES: tuple[OutputType, ...] = tuple(
    sorted(OUTPUT_TEMPLATES.keys(), key=lambda t: t.value)
)

_INITIAL_OUTPUTS: tuple[OutputSummary, ...] = (
    OutputSummary(
        output_id=OutputDocumentId("odoc_00000000000000000000000000000001"),
        label=OUTPUT_TEMPLATES[OutputType.PROFILE_REPORT].label,
        output_type=OutputType.PROFILE_REPORT,
        output_format=OutputFormat.JSON,
        succeeded=True,
    ),
    OutputSummary(
        output_id=OutputDocumentId("odoc_00000000000000000000000000000002"),
        label=OUTPUT_TEMPLATES[OutputType.FACT_EXPORT].label,
        output_type=OutputType.FACT_EXPORT,
        output_format=OutputFormat.JSON,
        succeeded=True,
    ),
    OutputSummary(
        output_id=OutputDocumentId("odoc_00000000000000000000000000000003"),
        label=OUTPUT_TEMPLATES[OutputType.CONFLICT_REPORT].label,
        output_type=OutputType.CONFLICT_REPORT,
        output_format=OutputFormat.JSON,
        succeeded=False,
    ),
)


class OutputsVM:

    def initial_outputs(self) -> tuple[OutputSummary, ...]:
        return _INITIAL_OUTPUTS

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

        new_id = generate_output_document_id()
        label = self.label_for(output_type)

        new_summary = OutputSummary(
            output_id=new_id,
            label=label,
            output_type=output_type,
            output_format=output_format,
            succeeded=True,
        )

        detail = OutputDetail(
            output_id=new_id,
            label=label,
            output_type=output_type,
            output_format=output_format,
            succeeded=True,
            file_path=f"outputs/{new_id}.json",
        )

        return GenerateResult(success=True, detail=detail), current_outputs + (
            new_summary,
        )
