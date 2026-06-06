from __future__ import annotations

from core.guards import require
from core.identifiers import is_valid_form_mapping_id, is_valid_form_template_id
from core.types import FormMappingId, FormTemplateId
from forms.form_mapping import FormMapping


class InMemoryFormMappingRepository:
    """
    Infrastructure Implementation.

    Implements FormMappingRepository Protocol using an in-memory dict.
    Intended for testing and early development only.

    Storage key: mapping_id (str)
    """

    def __init__(self) -> None:
        self._store: dict[FormMappingId, FormMapping] = {}

    def get_by_id(self, mapping_id: FormMappingId) -> FormMapping | None:
        require(is_valid_form_mapping_id(mapping_id), "mapping_id has invalid format")
        return self._store.get(mapping_id)

    def get_by_template_id(self, template_id: FormTemplateId) -> FormMapping | None:
        require(
            is_valid_form_template_id(template_id), "template_id has invalid format"
        )
        for mapping in self._store.values():
            if mapping.template_id == template_id:
                return mapping
        return None

    def save(self, mapping: FormMapping) -> None:
        require(isinstance(mapping, FormMapping), "mapping must be a FormMapping")
        self._store[mapping.mapping_id] = mapping

    def exists(self, mapping_id: FormMappingId) -> bool:
        require(is_valid_form_mapping_id(mapping_id), "mapping_id has invalid format")
        return mapping_id in self._store
