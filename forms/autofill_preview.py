from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import (
    is_valid_form_mapping_id,
    is_valid_form_template_id,
)
from core.types import FormMappingId, FormTemplateId
from forms.form_mapping import FormMapping, MappingFailureReason, MappingResult
from forms.form_submission import FormSubmission, SubmissionEntry
from forms.form_template import FormTemplate
from knowledge.knowledge_fact_type import KnowledgeFactType


class PreviewFieldStatus(StrEnum):
    FILLED = "filled"
    MISSING = "missing"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class PreviewField:
    field_name: str
    label: str
    suggested: Any | None
    status: PreviewFieldStatus
    failure_reason: MappingFailureReason | None = None

    def __post_init__(self) -> None:
        require(
            isinstance(self.field_name, str) and bool(self.field_name.strip()),
            "field_name must be a non-empty string",
        )
        require(
            isinstance(self.label, str) and bool(self.label.strip()),
            "label must be a non-empty string",
        )
        require(
            isinstance(self.status, PreviewFieldStatus),
            "status must be a PreviewFieldStatus",
        )


@dataclass(frozen=True)
class AutofillPreview:
    template_id: FormTemplateId
    mapping_id: FormMappingId
    preview_fields: tuple[PreviewField, ...]

    def __post_init__(self) -> None:
        require(
            is_valid_form_template_id(self.template_id),
            "template_id has invalid format",
        )
        require(
            is_valid_form_mapping_id(self.mapping_id),
            "mapping_id has invalid format",
        )
        require(
            isinstance(self.preview_fields, tuple) and len(self.preview_fields) > 0,
            "preview_fields must be a non-empty tuple",
        )
        require(
            all(isinstance(pf, PreviewField) for pf in self.preview_fields),
            "all preview_fields must be PreviewField instances",
        )

    @classmethod
    def build(
        cls,
        template: FormTemplate,
        mapping: FormMapping,
        facts: Mapping[KnowledgeFactType, Any],
    ) -> AutofillPreview:
        require(isinstance(template, FormTemplate), "template must be a FormTemplate")
        require(isinstance(mapping, FormMapping), "mapping must be a FormMapping")
        require(
            template.template_id == mapping.template_id,
            "template and mapping must share the same template_id",
        )
        require(isinstance(facts, Mapping), "facts must implement Mapping")

        results: tuple[MappingResult, ...] = mapping.apply(facts)

        preview_fields: list[PreviewField] = []
        for result in results:
            form_field = template.get_field(result.field_name)
            require(
                form_field is not None,
                f"field '{result.field_name}' not found in template",
            )
            assert form_field is not None  # narrow type for mypy

            if result.mapped:
                status = PreviewFieldStatus.FILLED
            elif result.rule.required:
                status = PreviewFieldStatus.MISSING
            else:
                status = PreviewFieldStatus.OPTIONAL

            preview_fields.append(
                PreviewField(
                    field_name=result.field_name,
                    label=form_field.label,
                    suggested=result.fact_value,
                    status=status,
                    failure_reason=result.failure_reason,
                )
            )

        return cls(
            template_id=template.template_id,
            mapping_id=mapping.mapping_id,
            preview_fields=tuple(preview_fields),
        )

    @property
    def filled_count(self) -> int:
        return sum(
            1 for pf in self.preview_fields if pf.status is PreviewFieldStatus.FILLED
        )

    @property
    def missing_count(self) -> int:
        return sum(
            1 for pf in self.preview_fields if pf.status is PreviewFieldStatus.MISSING
        )

    @property
    def optional_count(self) -> int:
        return sum(
            1 for pf in self.preview_fields if pf.status is PreviewFieldStatus.OPTIONAL
        )

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0

    def build_draft(self, template: FormTemplate) -> FormSubmission:
        require(isinstance(template, FormTemplate), "template must be a FormTemplate")
        require(
            template.template_id == self.template_id,
            "template must match preview template_id",
        )
        require(
            self.is_complete,
            "cannot create draft: preview has missing required fields",
        )

        entries: list[SubmissionEntry] = []
        for pf in self.preview_fields:
            if pf.status is PreviewFieldStatus.FILLED:
                form_field = template.get_field(pf.field_name)
                require(
                    form_field is not None,
                    f"field '{pf.field_name}' not found in template",
                )
                assert form_field is not None  # narrow type for mypy

                entries.append(
                    SubmissionEntry(
                        field_id=form_field.field_id,
                        value=pf.suggested,
                    )
                )

        return FormSubmission.create_draft(
            template_id=self.template_id,
            version=template.version,
            entries=tuple(entries),
        )
