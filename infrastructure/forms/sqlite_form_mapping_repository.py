from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

from core.guards import require
from core.identifiers import is_valid_form_mapping_id, is_valid_form_template_id
from core.types import FormMappingId, FormTemplateId
from forms.form_mapping import FormMapping, MappingRule
from infrastructure.db.sqlite_helpers import serialize_json
from knowledge.knowledge_fact_type import KnowledgeFactType

if TYPE_CHECKING:
    from infrastructure.db.connection import DatabaseConnection

_INSERT_OR_REPLACE = """
INSERT INTO form_mappings (
    mapping_id, template_id, rules
) VALUES (?, ?, ?)
ON CONFLICT(mapping_id) DO UPDATE SET
    template_id = excluded.template_id,
    rules       = excluded.rules
"""

_SELECT_BY_ID = """
SELECT mapping_id, template_id, rules
FROM form_mappings
WHERE mapping_id = ?
"""

_SELECT_BY_TEMPLATE_ID = """
SELECT mapping_id, template_id, rules
FROM form_mappings
WHERE template_id = ?
LIMIT 1
"""

_EXISTS = "SELECT 1 FROM form_mappings WHERE mapping_id = ? LIMIT 1"


def _rule_to_dict(rule: MappingRule) -> dict[str, Any]:
    return {
        "fact_type": rule.fact_type.value,
        "field_name": rule.field_name,
        "required": rule.required,
        "notes": rule.notes,
    }


def _rule_from_dict(d: dict[str, Any]) -> MappingRule:
    return MappingRule(
        fact_type=KnowledgeFactType(d["fact_type"]),
        field_name=d["field_name"],
        required=d["required"],
        notes=d.get("notes"),
    )


def _mapping_to_row(m: FormMapping) -> tuple[Any, ...]:
    return (
        m.mapping_id,
        m.template_id,
        json.dumps([_rule_to_dict(r) for r in m.rules]),
    )


def _row_to_mapping(row: sqlite3.Row) -> FormMapping:
    d = dict(row)
    rules = tuple(_rule_from_dict(r) for r in json.loads(d["rules"]))
    return FormMapping(
        mapping_id=FormMappingId(d["mapping_id"]),
        template_id=FormTemplateId(d["template_id"]),
        rules=rules,
    )


class SqliteFormMappingRepository:

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def save(self, mapping: FormMapping) -> None:
        require(isinstance(mapping, FormMapping), "mapping must be a FormMapping")
        self._conn.execute(_INSERT_OR_REPLACE, _mapping_to_row(mapping))
        self._conn.commit()

    def get_by_id(self, mapping_id: FormMappingId) -> FormMapping | None:
        require(
            is_valid_form_mapping_id(mapping_id),
            "mapping_id has invalid format",
        )
        row = self._conn.execute(_SELECT_BY_ID, (mapping_id,)).fetchone()
        return _row_to_mapping(row) if row else None

    def get_by_template_id(self, template_id: FormTemplateId) -> FormMapping | None:
        require(
            is_valid_form_template_id(template_id),
            "template_id has invalid format",
        )
        row = self._conn.execute(_SELECT_BY_TEMPLATE_ID, (template_id,)).fetchone()
        return _row_to_mapping(row) if row else None

    def exists(self, mapping_id: FormMappingId) -> bool:
        require(
            is_valid_form_mapping_id(mapping_id),
            "mapping_id has invalid format",
        )
        row = self._conn.execute(_EXISTS, (mapping_id,)).fetchone()
        return row is not None
