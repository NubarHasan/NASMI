from __future__ import annotations

from dataclasses import dataclass

from forms.autofill_engine import AutofillEngine
from forms.autofill_preview import AutofillPreview
from forms.form_field import FieldRule, FormField
from forms.form_mapping import FormMapping, MappingRule
from forms.form_submission import FormSubmission, SubmissionEntry
from forms.form_template import FormTemplate
from forms.form_type import FieldType, FormKind, SubmissionStatus
from knowledge.knowledge_fact_type import KnowledgeFactType

_FIELD_TO_FACT: dict[str, KnowledgeFactType] = {
    "full_name": KnowledgeFactType.PERSON_FULL_NAME,
    "date_of_birth": KnowledgeFactType.DATE_OF_BIRTH,
    "nationality": KnowledgeFactType.NATIONALITY,
    "passport_number": KnowledgeFactType.PASSPORT_NUMBER,
    "address": KnowledgeFactType.ADDRESS_STREET,
    "email": KnowledgeFactType.EMAIL_ADDRESS,
    "phone": KnowledgeFactType.PHONE_NUMBER,
    "tax_id": KnowledgeFactType.TAX_ID,
    "annual_income": KnowledgeFactType.TAX_ID,
}


def _make_stub_templates() -> tuple[FormTemplate, ...]:
    passport_fields = (
        FormField.create(
            field_name="full_name",
            label="Full Name",
            field_type=FieldType.TEXT,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="date_of_birth",
            label="Date of Birth",
            field_type=FieldType.DATE,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="nationality",
            label="Nationality",
            field_type=FieldType.TEXT,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="passport_number",
            label="Passport Number",
            field_type=FieldType.TEXT,
            rules=(FieldRule.required(),),
        ),
    )

    residence_fields = (
        FormField.create(
            field_name="full_name",
            label="Full Name",
            field_type=FieldType.TEXT,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="address",
            label="Address",
            field_type=FieldType.TEXTAREA,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="email",
            label="Email",
            field_type=FieldType.EMAIL,
        ),
        FormField.create(
            field_name="phone",
            label="Phone",
            field_type=FieldType.PHONE,
        ),
    )

    tax_fields = (
        FormField.create(
            field_name="full_name",
            label="Full Name",
            field_type=FieldType.TEXT,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="tax_id",
            label="Tax ID",
            field_type=FieldType.TEXT,
            rules=(FieldRule.required(),),
        ),
        FormField.create(
            field_name="annual_income",
            label="Annual Income",
            field_type=FieldType.DECIMAL,
        ),
    )

    return (
        FormTemplate.create(
            name="Passport Application",
            form_kind=FormKind.PASSPORT,
            fields=passport_fields,
        ),
        FormTemplate.create(
            name="Residence Permit",
            form_kind=FormKind.RESIDENCE_PERMIT,
            fields=residence_fields,
        ),
        FormTemplate.create(
            name="Tax Form",
            form_kind=FormKind.TAX_FORM,
            fields=tax_fields,
        ),
    )


_STUB_TEMPLATES: tuple[FormTemplate, ...] = _make_stub_templates()


@dataclass(frozen=True)
class TemplateSummary:
    template_id: str
    name: str
    form_kind: FormKind
    field_count: int
    version: int


@dataclass(frozen=True)
class SubmissionSummary:
    submission_id: str
    template_name: str
    status: SubmissionStatus
    entry_count: int


@dataclass(frozen=True)
class AutofillResult:
    success: bool
    preview: AutofillPreview | None = None
    error: str | None = None


@dataclass(frozen=True)
class SubmitResult:
    success: bool
    submission: FormSubmission | None = None
    error: str | None = None


class FormsVM:

    def list_templates(self) -> tuple[TemplateSummary, ...]:
        return tuple(
            TemplateSummary(
                template_id=t.template_id,
                name=t.name,
                form_kind=t.form_kind,
                field_count=t.field_count,
                version=t.version,
            )
            for t in _STUB_TEMPLATES
        )

    def get_template(self, template_id: str) -> FormTemplate | None:
        for t in _STUB_TEMPLATES:
            if t.template_id == template_id:
                return t
        return None

    def autofill(self, template_id: str) -> AutofillResult:
        template = self.get_template(template_id)
        if template is None:
            return AutofillResult(success=False, error="Template not found.")

        rules: list[MappingRule] = []
        for f in template.fields:
            fact_type = _FIELD_TO_FACT.get(f.field_name)
            if fact_type is not None:
                rules.append(
                    MappingRule(
                        fact_type=fact_type,
                        field_name=f.field_name,
                        required=f.is_required,
                    )
                )

        if not rules:
            return AutofillResult(success=False, error="No mappable fields found.")

        try:
            mapping = FormMapping(
                template_id=template.template_id,
                rules=tuple(rules),
            )
            preview = AutofillEngine().run(
                template=template,
                mapping=mapping,
                facts={},
            )
            return AutofillResult(success=True, preview=preview)
        except Exception as exc:
            return AutofillResult(success=False, error=str(exc))

    def build_draft(
        self,
        template_id: str,
        field_values: dict[str, str],
    ) -> SubmitResult:
        template = self.get_template(template_id)
        if template is None:
            return SubmitResult(success=False, error="Template not found.")

        entries: list[SubmissionEntry] = []
        for field in template.fields:
            value = field_values.get(field.field_name)
            if value is None or str(value).strip() == "":
                if field.is_required:
                    return SubmitResult(
                        success=False,
                        error=f"Required field missing: {field.label}",
                    )
                continue
            entries.append(
                SubmissionEntry(field_id=field.field_id, value=str(value).strip())
            )

        if not entries:
            return SubmitResult(success=False, error="No field values provided.")

        try:
            submission = FormSubmission.create_draft(
                template_id=template.template_id,
                version=template.version,
                entries=tuple(entries),
            )
            return SubmitResult(success=True, submission=submission)
        except Exception as exc:
            return SubmitResult(success=False, error=str(exc))

    def submit(self, submission: FormSubmission) -> SubmitResult:
        try:
            return SubmitResult(success=True, submission=submission.submit())
        except Exception as exc:
            return SubmitResult(success=False, error=str(exc))

    def kind_label(self, form_kind: FormKind) -> str:
        labels: dict[FormKind, str] = {
            FormKind.PASSPORT: "Passport",
            FormKind.RESIDENCE_PERMIT: "Residence Permit",
            FormKind.BIRTH_CERTIFICATE: "Birth Certificate",
            FormKind.MARRIAGE_CERTIFICATE: "Marriage Certificate",
            FormKind.TAX_FORM: "Tax Form",
            FormKind.BANK_FORM: "Bank Form",
            FormKind.EMPLOYMENT: "Employment",
            FormKind.CUSTOM: "Custom",
        }
        return labels.get(form_kind, form_kind.value)

    def status_badge(self, status: SubmissionStatus) -> str:
        return "📝 Draft" if status is SubmissionStatus.DRAFT else "✅ Submitted"
