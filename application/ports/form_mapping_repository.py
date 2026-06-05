from __future__ import annotations

from typing import Protocol

from core.types import FormMappingId, FormTemplateId
from forms.form_mapping import FormMapping


class FormMappingRepository(Protocol):

    def get_by_id(self, mapping_id: FormMappingId) -> FormMapping | None:
        """Return FormMapping by ID, or None if not found."""
        ...

    def get_by_template_id(self, template_id: FormTemplateId) -> FormMapping | None:
        """Return the mapping associated with a given template, or None."""
        ...

    def save(self, mapping: FormMapping) -> None:
        """Persist a new or updated FormMapping."""
        ...

    def exists(self, mapping_id: FormMappingId) -> bool:
        """Return True if a mapping with this ID exists."""
        ...
