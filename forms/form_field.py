from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.identifiers import generate_form_field_id, is_valid_form_field_id
from core.types import FieldValue, FormFieldId
from forms.form_type import FieldType


class RuleType(StrEnum):
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"
    ALLOWED_VALUES = "allowed_values"


@dataclass(frozen=True)
class FieldRule:
    rule_type: RuleType
    parameter: Any | None

    def __post_init__(self) -> None:
        require(isinstance(self.rule_type, RuleType), "rule_type must be a RuleType")

    @classmethod
    def create(
        cls,
        rule_type: RuleType,
        parameter: Any | None = None,
    ) -> FieldRule:
        require(isinstance(rule_type, RuleType), "rule_type must be a RuleType")
        return cls(rule_type=rule_type, parameter=parameter)

    @classmethod
    def required(cls) -> FieldRule:
        return cls.create(RuleType.REQUIRED)

    @classmethod
    def min_length(cls, value: int) -> FieldRule:
        require(isinstance(value, int), "min_length parameter must be an integer")
        require(value >= 0, "min_length must be >= 0")
        return cls.create(RuleType.MIN_LENGTH, value)

    @classmethod
    def max_length(cls, value: int) -> FieldRule:
        require(isinstance(value, int), "max_length parameter must be an integer")
        require(value > 0, "max_length must be > 0")
        return cls.create(RuleType.MAX_LENGTH, value)

    @classmethod
    def min_value(cls, value: int | float) -> FieldRule:
        require(isinstance(value, (int, float)), "min_value parameter must be numeric")
        return cls.create(RuleType.MIN_VALUE, value)

    @classmethod
    def max_value(cls, value: int | float) -> FieldRule:
        require(isinstance(value, (int, float)), "max_value parameter must be numeric")
        return cls.create(RuleType.MAX_VALUE, value)

    @classmethod
    def pattern(cls, regex: str) -> FieldRule:
        require(isinstance(regex, str), "pattern parameter must be a string")
        require(bool(regex.strip()), "pattern must not be empty")
        return cls.create(RuleType.PATTERN, regex.strip())

    @classmethod
    def allowed_values(cls, values: list[str]) -> FieldRule:
        require(isinstance(values, list), "allowed_values parameter must be a list")
        require(len(values) > 0, "allowed_values must not be empty")
        require(
            all(isinstance(v, str) for v in values),
            "all allowed_values must be strings",
        )
        return cls.create(RuleType.ALLOWED_VALUES, tuple(values))


@dataclass(frozen=True)
class FormField:
    field_id: FormFieldId
    field_name: str
    label: str
    field_type: FieldType
    default_value: FieldValue
    rules: tuple[FieldRule, ...]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        require(is_valid_form_field_id(self.field_id), "field_id has invalid format")
        require(isinstance(self.field_name, str), "field_name must be a string")
        require(bool(self.field_name.strip()), "field_name must not be empty")
        require(isinstance(self.label, str), "label must be a string")
        require(bool(self.label.strip()), "label must not be empty")
        require(
            isinstance(self.field_type, FieldType), "field_type must be a FieldType"
        )
        require(isinstance(self.rules, tuple), "rules must be a tuple")
        require(
            all(isinstance(r, FieldRule) for r in self.rules),
            "all rules must be FieldRule instances",
        )
        require(isinstance(self.metadata, Mapping), "metadata must be a Mapping")

    @classmethod
    def create(
        cls,
        field_name: str,
        label: str,
        field_type: FieldType,
        default_value: FieldValue = None,
        rules: tuple[FieldRule, ...] | None = None,
        metadata: Mapping[str, Any] | None = None,
        field_id: FormFieldId | None = None,
    ) -> FormField:
        require(isinstance(field_name, str), "field_name must be a string")
        require(bool(field_name.strip()), "field_name must not be empty")
        require(isinstance(label, str), "label must be a string")
        require(bool(label.strip()), "label must not be empty")
        require(isinstance(field_type, FieldType), "field_type must be a FieldType")

        resolved_rules = rules if rules is not None else ()
        require(isinstance(resolved_rules, tuple), "rules must be a tuple")
        require(
            all(isinstance(r, FieldRule) for r in resolved_rules),
            "all rules must be FieldRule instances",
        )

        resolved_id = field_id if field_id is not None else generate_form_field_id()
        require(is_valid_form_field_id(resolved_id), "field_id has invalid format")

        resolved_metadata = MappingProxyType(
            dict(metadata) if metadata is not None else {}
        )

        return cls(
            field_id=resolved_id,
            field_name=field_name.strip(),
            label=label.strip(),
            field_type=field_type,
            default_value=default_value,
            rules=resolved_rules,
            metadata=resolved_metadata,
        )

    @property
    def is_required(self) -> bool:
        return any(r.rule_type == RuleType.REQUIRED for r in self.rules)

    @property
    def has_default(self) -> bool:
        return self.default_value is not None

    def get_rule(self, rule_type: RuleType) -> FieldRule | None:
        require(isinstance(rule_type, RuleType), "rule_type must be a RuleType")
        for rule in self.rules:
            if rule.rule_type == rule_type:
                return rule
        return None

    def with_rule(self, rule: FieldRule) -> FormField:
        require(isinstance(rule, FieldRule), "rule must be a FieldRule")
        updated = tuple(r for r in self.rules if r.rule_type != rule.rule_type) + (
            rule,
        )
        return FormField(
            field_id=self.field_id,
            field_name=self.field_name,
            label=self.label,
            field_type=self.field_type,
            default_value=self.default_value,
            rules=updated,
            metadata=self.metadata,
        )

    def without_rule(self, rule_type: RuleType) -> FormField:
        require(isinstance(rule_type, RuleType), "rule_type must be a RuleType")
        return FormField(
            field_id=self.field_id,
            field_name=self.field_name,
            label=self.label,
            field_type=self.field_type,
            default_value=self.default_value,
            rules=tuple(r for r in self.rules if r.rule_type != rule_type),
            metadata=self.metadata,
        )
