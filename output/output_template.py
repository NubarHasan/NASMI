from dataclasses import dataclass
from types import MappingProxyType

from core.validation import require

from output.output_format import OutputFormat
from output.output_source import OutputSource
from output.output_type import OutputType


@dataclass(frozen=True)
class OutputTemplate:
    output_type: OutputType
    supported_formats: frozenset[OutputFormat]
    required_sources: frozenset[OutputSource]
    label: str
    description: str

    def __post_init__(self) -> None:
        require(len(self.supported_formats) > 0, "supported_formats must not be empty")
        require(len(self.required_sources) > 0, "required_sources must not be empty")
        require(bool(self.label.strip()), "label must not be blank")
        require(bool(self.description.strip()), "description must not be blank")


def _build_registry(
    templates: tuple[OutputTemplate, ...],
) -> dict[OutputType, OutputTemplate]:
    registry: dict[OutputType, OutputTemplate] = {}
    for template in templates:
        require(
            template.output_type not in registry,
            f"duplicate OutputType in registry: {template.output_type}",
        )
        registry[template.output_type] = template
    return registry


_RAW: tuple[OutputTemplate, ...] = (
    OutputTemplate(
        output_type=OutputType.PROFILE_REPORT,
        supported_formats=frozenset({OutputFormat.PDF, OutputFormat.DOCX}),
        required_sources=frozenset({OutputSource.PROFILE, OutputSource.ACCEPTED_FACTS}),
        label="Profile Report",
        description="A structured report summarising the subject profile and accepted facts.",
    ),
    OutputTemplate(
        output_type=OutputType.KNOWLEDGE_REPORT,
        supported_formats=frozenset({OutputFormat.PDF, OutputFormat.DOCX}),
        required_sources=frozenset(
            {OutputSource.KNOWLEDGE_VAULT, OutputSource.ACCEPTED_FACTS}
        ),
        label="Knowledge Report",
        description="A comprehensive report of all knowledge held about a subject.",
    ),
    OutputTemplate(
        output_type=OutputType.FACT_EXPORT,
        supported_formats=frozenset(
            {OutputFormat.JSON, OutputFormat.XML, OutputFormat.CSV}
        ),
        required_sources=frozenset({OutputSource.ACCEPTED_FACTS}),
        label="Fact Export",
        description="A structured export of accepted facts in machine-readable format.",
    ),
    OutputTemplate(
        output_type=OutputType.EVIDENCE_REPORT,
        supported_formats=frozenset({OutputFormat.PDF, OutputFormat.DOCX}),
        required_sources=frozenset(
            {OutputSource.EVIDENCE, OutputSource.ACCEPTED_FACTS}
        ),
        label="Evidence Report",
        description="A report linking accepted facts to their supporting evidence.",
    ),
    OutputTemplate(
        output_type=OutputType.PROVENANCE_REPORT,
        supported_formats=frozenset(
            {OutputFormat.PDF, OutputFormat.DOCX, OutputFormat.JSON}
        ),
        required_sources=frozenset(
            {OutputSource.PROVENANCE, OutputSource.ARCHIVE_DOCUMENTS}
        ),
        label="Provenance Report",
        description="A report tracing the origin and chain of custody of each fact.",
    ),
    OutputTemplate(
        output_type=OutputType.CONFLICT_REPORT,
        supported_formats=frozenset({OutputFormat.PDF, OutputFormat.DOCX}),
        required_sources=frozenset(
            {OutputSource.CONFLICTS, OutputSource.FACTS, OutputSource.EVIDENCE}
        ),
        label="Conflict Report",
        description="A report documenting detected conflicts between facts and their resolution status.",
    ),
    OutputTemplate(
        output_type=OutputType.AUDIT_REPORT,
        supported_formats=frozenset({OutputFormat.PDF, OutputFormat.JSON}),
        required_sources=frozenset({OutputSource.AUDIT_CHAIN}),
        label="Audit Report",
        description="A tamper-evident report of the full audit chain for a subject.",
    ),
    OutputTemplate(
        output_type=OutputType.FORM_SUBMISSION,
        supported_formats=frozenset({OutputFormat.PDF, OutputFormat.DOCX}),
        required_sources=frozenset(
            {
                OutputSource.FORM_TEMPLATE,
                OutputSource.FORM_SUBMISSION,
                OutputSource.ACCEPTED_FACTS,
            }
        ),
        label="Form Submission",
        description="A completed form populated with accepted facts and submission data.",
    ),
    OutputTemplate(
        output_type=OutputType.APPLICATION_PACKAGE,
        supported_formats=frozenset({OutputFormat.ZIP}),
        required_sources=frozenset(
            {
                OutputSource.PROFILE,
                OutputSource.ACCEPTED_FACTS,
                OutputSource.EVIDENCE,
                OutputSource.FORM_SUBMISSION,
                OutputSource.AUDIT_CHAIN,
            }
        ),
        label="Application Package",
        description="A complete application bundle containing all required documents and data.",
    ),
)

OUTPUT_TEMPLATES: MappingProxyType[OutputType, OutputTemplate] = MappingProxyType(
    _build_registry(_RAW)
)
