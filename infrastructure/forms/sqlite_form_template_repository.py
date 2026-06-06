from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from core.guards import require
from core.identifiers import is_valid_form_template_id
from core.types import FormFieldId, FormTemplateId
from forms.form_field import FieldRule, FormField, RuleType
from forms.form_template import FormTemplate
from forms.form_type import FieldType, FormKind
from infrastructure.db.sqlite_helpers import deserialize_json, serialize_json

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection

_INSERT_OR_REPLACE = """
INSERT INTO form_templates (
    template_id, name, form_kind, version,
    fields, created_at, metadata
) VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(template_id) DO UPDATE SET
    name       = excluded.name,
    form_kind  = excluded.form_kind,
    version    = excluded.version,
    fields     = excluded.fields,
    created_at = excluded.created_at,
    metadata   = excluded.metadata
"""

_SELECT_BY_ID = """
SELECT template_id, name, form_kind, version,
       fields, created_at, metadata
FROM form_templates
WHERE template_id = ?
"""

_SELECT_BY_KIND = """
SELECT template_id, name, form_kind, version,
       fields, created_at, metadata
FROM form_templates
WHERE form_kind = ?
ORDER BY version DESC
"""

_EXISTS = "SELECT 1 FROM form_templates WHERE template_id = ? LIMIT 1"


def _rule_to_dict(rule: FieldRule) -> dict[str, Any]:
    return {"rule_type": rule.rule_type.value, "parameter": rule.parameter}


def _rule_from_dict(d: dict[str, Any]) -> FieldRule:
    return FieldRule(
        rule_type=RuleType(d["rule_type"]),
        parameter=d.get("parameter"),
    )


def _field_to_dict(f: FormField) -> dict[str, Any]:
    return {
        "field_id": f.field_id,
        "field_name": f.field_name,
        "label": f.label,
        "field_type": f.field_type.value,
        "default_value": f.default_value,
        "rules": [_rule_to_dict(r) for r in f.rules],
        "metadata": dict(f.metadata),
    }


def _field_from_dict(d: dict[str, Any]) -> FormField:
    return FormField(
        field_id=FormFieldId(d["field_id"]),
        field_name=d["field_name"],
        label=d["label"],
        field_type=FieldType(d["field_type"]),
        default_value=d.get("default_value"),
        rules=tuple(_rule_from_dict(r) for r in d.get("rules", [])),
        metadata=d.get("metadata", {}),
    )


def _template_to_row(t: FormTemplate) -> tuple[Any, ...]:
    return (
        t.template_id,
        t.name,
        t.form_kind.value,
        t.version,
        json.dumps([_field_to_dict(f) for f in t.fields]),
        t.created_at.isoformat(),
        serialize_json(dict(t.metadata)),
    )


def _row_to_template(row: sqlite3.Row) -> FormTemplate:
    d = dict(row)
    fields = tuple(_field_from_dict(f) for f in json.loads(d["fields"]))
    return FormTemplate(
        template_id=FormTemplateId(d["template_id"]),
        name=d["name"],
        form_kind=FormKind(d["form_kind"]),
        version=d["version"],
        fields=fields,
        created_at=datetime.fromisoformat(d["created_at"]).replace(tzinfo=UTC),
        metadata=deserialize_json(d["metadata"]),
    )


class SqliteFormTemplateRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, template: FormTemplate) -> None:
        require(isinstance(template, FormTemplate), "template must be a FormTemplate")
        self._conn.execute(_INSERT_OR_REPLACE, _template_to_row(template))
        self._conn.commit()

    def get_by_id(self, template_id: FormTemplateId) -> FormTemplate | None:
        require(
            is_valid_form_template_id(template_id),
            "template_id has invalid format",
        )
        row = self._conn.execute(_SELECT_BY_ID, (template_id,)).fetchone()
        return _row_to_template(row) if row else None

    def get_by_kind(self, form_kind: FormKind) -> list[FormTemplate]:
        require(isinstance(form_kind, FormKind), "form_kind must be a FormKind")
        rows = self._conn.execute(_SELECT_BY_KIND, (form_kind.value,)).fetchall()
        return [_row_to_template(r) for r in rows]

    def get_latest_by_kind(self, form_kind: FormKind) -> FormTemplate | None:
        results = self.get_by_kind(form_kind)
        return results[0] if results else None

    def exists(self, template_id: FormTemplateId) -> bool:
        require(
            is_valid_form_template_id(template_id),
            "template_id has invalid format",
        )
        row = self._conn.execute(_EXISTS, (template_id,)).fetchone()
        return row is not None
