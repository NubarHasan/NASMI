from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.identifiers import generate_form_template_id, is_valid_form_template_id
from core.types import FormTemplateId
from forms.form_field import FormField
from forms.form_type import FormKind


def _require_unique_fields(fields: tuple[FormField, ...]) -> None:
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for f in fields:
        require(f.field_id not in seen_ids, f"duplicate field_id: {f.field_id}")
        require(f.field_name not in seen_names, f"duplicate field_name: {f.field_name}")
        seen_ids.add(f.field_id)
        seen_names.add(f.field_name)


@dataclass(frozen=True)
class FormTemplate:
    template_id: FormTemplateId
    name: str
    form_kind: FormKind
    version: int
    fields: tuple[FormField, ...]
    created_at: datetime
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        require(
            is_valid_form_template_id(self.template_id),
            "template_id has invalid format",
        )
        require(isinstance(self.name, str), "name must be a string")
        require(bool(self.name.strip()), "name must not be empty")
        require(isinstance(self.form_kind, FormKind), "form_kind must be a FormKind")
        require(isinstance(self.version, int), "version must be an integer")
        require(self.version >= 1, "version must be >= 1")
        require(isinstance(self.fields, tuple), "fields must be a tuple")
        require(
            all(isinstance(f, FormField) for f in self.fields),
            "all fields must be FormField instances",
        )
        require(len(self.fields) > 0, "template must contain at least one field")
        _require_unique_fields(self.fields)
        require(isinstance(self.created_at, datetime), "created_at must be a datetime")
        require(self.created_at.tzinfo is not None, "created_at must be timezone-aware")
        require(isinstance(self.metadata, Mapping), "metadata must be a Mapping")

    @classmethod
    def create(
        cls,
        name: str,
        form_kind: FormKind,
        fields: tuple[FormField, ...],
        version: int = 1,
        metadata: Mapping[str, Any] | None = None,
        template_id: FormTemplateId | None = None,
        created_at: datetime | None = None,
    ) -> FormTemplate:
        require(isinstance(name, str), "name must be a string")
        require(bool(name.strip()), "name must not be empty")
        require(isinstance(form_kind, FormKind), "form_kind must be a FormKind")
        require(isinstance(version, int), "version must be an integer")
        require(version >= 1, "version must be >= 1")
        require(isinstance(fields, tuple), "fields must be a tuple")
        require(
            all(isinstance(f, FormField) for f in fields),
            "all fields must be FormField instances",
        )
        require(len(fields) > 0, "template must contain at least one field")
        _require_unique_fields(fields)

        resolved_id = (
            template_id if template_id is not None else generate_form_template_id()
        )
        require(
            is_valid_form_template_id(resolved_id), "template_id has invalid format"
        )

        resolved_at = created_at if created_at is not None else datetime.now(UTC)
        require(resolved_at.tzinfo is not None, "created_at must be timezone-aware")

        resolved_metadata = MappingProxyType(
            dict(metadata) if metadata is not None else {}
        )

        return cls(
            template_id=resolved_id,
            name=name.strip(),
            form_kind=form_kind,
            version=version,
            fields=fields,
            created_at=resolved_at,
            metadata=resolved_metadata,
        )

    @property
    def field_count(self) -> int:
        return len(self.fields)

    def get_field(self, field_name: str) -> FormField | None:
        require(isinstance(field_name, str), "field_name must be a string")
        require(bool(field_name.strip()), "field_name must not be empty")
        for f in self.fields:
            if f.field_name == field_name.strip():
                return f
        return None

    def has_field(self, field_name: str) -> bool:
        return self.get_field(field_name) is not None

    def next_version(self, new_fields: tuple[FormField, ...]) -> FormTemplate:
        require(isinstance(new_fields, tuple), "new_fields must be a tuple")
        require(
            all(isinstance(f, FormField) for f in new_fields),
            "all new_fields must be FormField instances",
        )
        require(len(new_fields) > 0, "template must contain at least one field")
        _require_unique_fields(new_fields)
        return FormTemplate.create(
            name=self.name,
            form_kind=self.form_kind,
            fields=new_fields,
            version=self.version + 1,
            metadata=self.metadata,
        )
