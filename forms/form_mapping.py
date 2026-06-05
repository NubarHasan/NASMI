from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_form_mapping_id,
    is_valid_form_mapping_id,
    is_valid_form_template_id,
)
from core.types import FormMappingId, FormTemplateId
from knowledge.knowledge_fact_type import KnowledgeFactType


class MappingFailureReason(StrEnum):
    FACT_NOT_FOUND = "fact_not_found"
    MULTIPLE_FACTS_FOUND = "multiple_facts_found"
    INVALID_VALUE = "invalid_value"


@dataclass(frozen=True)
class MappingRule:
    fact_type: KnowledgeFactType
    field_name: str
    required: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        require(
            isinstance(self.fact_type, KnowledgeFactType),
            "fact_type must be a KnowledgeFactType",
        )
        require(
            isinstance(self.field_name, str) and bool(self.field_name.strip()),
            "field_name must be a non-empty string",
        )


@dataclass(frozen=True)
class MappingResult:
    rule: MappingRule
    fact_value: Any | None
    mapped: bool
    failure_reason: MappingFailureReason | None = None

    @property
    def field_name(self) -> str:
        return self.rule.field_name

    @property
    def is_missing(self) -> bool:
        return self.rule.required and not self.mapped

    def __repr__(self) -> str:
        if self.mapped:
            status = "✓"
        elif self.failure_reason:
            status = f"✗ {self.failure_reason}"
        elif self.rule.required:
            status = "✗ required"
        else:
            status = "– optional"
        return (
            f"MappingResult("
            f"fact_type={self.rule.fact_type!r}, "
            f"field_name={self.field_name!r}, "
            f"value={self.fact_value!r}, "
            f"status={status})"
        )


@dataclass(frozen=True)
class FormMapping:
    template_id: FormTemplateId
    rules: tuple[MappingRule, ...]
    mapping_id: FormMappingId = field(default_factory=generate_form_mapping_id)

    def __post_init__(self) -> None:
        require(
            is_valid_form_mapping_id(self.mapping_id),
            "mapping_id has invalid format",
        )
        require(
            is_valid_form_template_id(self.template_id),
            "template_id has invalid format",
        )
        require(
            isinstance(self.rules, tuple) and len(self.rules) > 0,
            "rules must be a non-empty tuple",
        )
        require(
            all(isinstance(rule, MappingRule) for rule in self.rules),
            "all rules must be MappingRule instances",
        )
        fact_types = [r.fact_type for r in self.rules]
        field_names = [r.field_name for r in self.rules]
        require(
            len(fact_types) == len(set(fact_types)),
            "FormMapping contains duplicate fact_type entries",
        )
        require(
            len(field_names) == len(set(field_names)),
            "FormMapping contains duplicate field_name entries",
        )

    def apply(
        self, facts: Mapping[KnowledgeFactType, Any]
    ) -> tuple[MappingResult, ...]:
        require(
            isinstance(facts, Mapping),
            "facts must implement Mapping",
        )
        results = []
        for rule in self.rules:
            if rule.fact_type in facts:
                results.append(
                    MappingResult(
                        rule=rule,
                        fact_value=facts[rule.fact_type],
                        mapped=True,
                    )
                )
            else:
                results.append(
                    MappingResult(
                        rule=rule,
                        fact_value=None,
                        mapped=False,
                        failure_reason=MappingFailureReason.FACT_NOT_FOUND,
                    )
                )
        return tuple(results)

    def missing(
        self, facts: Mapping[KnowledgeFactType, Any]
    ) -> tuple[MappingResult, ...]:
        return tuple(r for r in self.apply(facts) if r.is_missing)

    def is_complete(self, facts: Mapping[KnowledgeFactType, Any]) -> bool:
        return len(self.missing(facts)) == 0
