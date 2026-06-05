from __future__ import annotations

from typing import Protocol

from core.types import FormTemplateId
from forms.form_template import FormTemplate
from forms.form_type import FormKind


class FormTemplateRepository(Protocol):

    def get_by_id(self, template_id: FormTemplateId) -> FormTemplate | None:
        """Return FormTemplate by ID, or None if not found."""
        ...

    def get_by_kind(self, form_kind: FormKind) -> tuple[FormTemplate, ...]:
        """Return all templates for a given FormKind, ordered by version descending."""
        ...

    def get_latest_by_kind(self, form_kind: FormKind) -> FormTemplate | None:
        """Return the highest-version template for a given FormKind, or None."""
        ...

    def save(self, template: FormTemplate) -> None:
        """Persist a new or updated FormTemplate."""
        ...

    def exists(self, template_id: FormTemplateId) -> bool:
        """Return True if a template with this ID exists."""
        ...
