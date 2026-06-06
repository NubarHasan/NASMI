from __future__ import annotations

from core.guards import require
from core.identifiers import is_valid_form_template_id
from core.types import FormTemplateId
from forms.form_template import FormTemplate
from forms.form_type import FormKind


class InMemoryFormTemplateRepository:
    """
    Infrastructure Implementation.

    Implements FormTemplateRepository Protocol using an in-memory dict.
    Intended for testing and early development only.

    Storage key: template_id (str)
    """

    def __init__(self) -> None:
        self._store: dict[FormTemplateId, FormTemplate] = {}

    def get_by_id(self, template_id: FormTemplateId) -> FormTemplate | None:
        require(
            is_valid_form_template_id(template_id), "template_id has invalid format"
        )
        return self._store.get(template_id)

    def get_by_kind(self, form_kind: FormKind) -> tuple[FormTemplate, ...]:
        require(isinstance(form_kind, FormKind), "form_kind must be a FormKind")
        return tuple(
            sorted(
                (t for t in self._store.values() if t.form_kind is form_kind),
                key=lambda t: t.version,
                reverse=True,
            )
        )

    def get_latest_by_kind(self, form_kind: FormKind) -> FormTemplate | None:
        require(isinstance(form_kind, FormKind), "form_kind must be a FormKind")
        results = self.get_by_kind(form_kind)
        return results[0] if results else None

    def save(self, template: FormTemplate) -> None:
        require(isinstance(template, FormTemplate), "template must be a FormTemplate")
        self._store[template.template_id] = template

    def exists(self, template_id: FormTemplateId) -> bool:
        require(
            is_valid_form_template_id(template_id), "template_id has invalid format"
        )
        return template_id in self._store
