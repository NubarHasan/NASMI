from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Never, TypeAlias

from core.guards import require
from processing.extraction.candidate_fact import CandidateFact
from processing.validation.date_formats import DATE_FORMATS
from processing.validation.validation_context import ValidationContext
from processing.validation.validation_report import (
    RuleResult,
    ValidationSeverity,
)


class ComparisonType(StrEnum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    DATE = "DATE"


class ConsistencyRelation(StrEnum):
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"


Comparable: TypeAlias = datetime | float | str


def _parse_date(value: str) -> datetime | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _parse_number(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _unreachable(relation: ConsistencyRelation) -> Never:
    raise AssertionError(f"unsupported relation [{relation}]")


def _compare(lhs: Comparable, rhs: Comparable, relation: ConsistencyRelation) -> bool:
    if relation is ConsistencyRelation.EQUAL:
        return lhs == rhs
    if relation is ConsistencyRelation.NOT_EQUAL:
        return lhs != rhs
    if relation is ConsistencyRelation.LESS_THAN:
        return lhs < rhs
    if relation is ConsistencyRelation.LESS_THAN_OR_EQUAL:
        return lhs <= rhs
    if relation is ConsistencyRelation.GREATER_THAN:
        return lhs > rhs
    if relation is ConsistencyRelation.GREATER_THAN_OR_EQUAL:
        return lhs >= rhs
    return _unreachable(relation)


@dataclass(frozen=True)
class ConsistencyRule:

    rule_id: str
    rule_name: str
    primary_fact_type: str
    dependent_fact_type: str
    relation: ConsistencyRelation
    comparison_type: ComparisonType
    severity: ValidationSeverity = ValidationSeverity.ERROR

    def __post_init__(self) -> None:
        require(bool(self.rule_id.strip()), "rule_id must not be blank")
        require(bool(self.rule_name.strip()), "rule_name must not be blank")
        require(
            bool(self.primary_fact_type.strip()), "primary_fact_type must not be blank"
        )
        require(
            bool(self.dependent_fact_type.strip()),
            "dependent_fact_type must not be blank",
        )
        require(
            self.primary_fact_type != self.dependent_fact_type,
            "primary_fact_type and dependent_fact_type must be different",
        )
        require(
            isinstance(self.relation, ConsistencyRelation),
            "relation must be a ConsistencyRelation",
        )
        require(
            isinstance(self.comparison_type, ComparisonType),
            "comparison_type must be a ComparisonType",
        )
        require(
            isinstance(self.severity, ValidationSeverity),
            "severity must be a ValidationSeverity",
        )
        require(
            not (
                self.comparison_type is ComparisonType.STRING
                and self.relation
                not in (
                    ConsistencyRelation.EQUAL,
                    ConsistencyRelation.NOT_EQUAL,
                )
            ),
            "STRING comparison_type only supports EQUAL and NOT_EQUAL relations",
        )

    def evaluate(
        self,
        candidate_fact: CandidateFact,
        context: ValidationContext,
    ) -> RuleResult:
        if candidate_fact.fact_type != self.primary_fact_type:
            return RuleResult.passed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"fact_type [{candidate_fact.fact_type}] not targeted by this rule",
            )

        dependent_facts = context.accepted_for_field(self.dependent_fact_type)

        if not dependent_facts:
            return RuleResult.passed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=(
                    f"dependent fact [{self.dependent_fact_type}] "
                    f"not available; consistency check skipped"
                ),
            )

        require(
            len(dependent_facts) == 1,
            f"expected exactly one accepted fact for [{self.dependent_fact_type}], "
            f"found [{len(dependent_facts)}]",
        )

        dependent_fact = dependent_facts[0]
        primary_value = candidate_fact.normalized_value
        dependent_value = dependent_fact.canonical_value

        if self.comparison_type is ComparisonType.DATE:
            return self._evaluate_date(primary_value, dependent_value)

        if self.comparison_type is ComparisonType.NUMBER:
            return self._evaluate_number(primary_value, dependent_value)

        return self._evaluate_string(primary_value, dependent_value)

    def _evaluate_date(self, primary_value: str, dependent_value: str) -> RuleResult:
        primary_dt = _parse_date(primary_value)
        if primary_dt is None:
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"primary value [{primary_value}] could not be parsed as a date",
                severity=self.severity,
            )

        dependent_dt = _parse_date(dependent_value)
        if dependent_dt is None:
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"dependent value [{dependent_value}] could not be parsed as a date",
                severity=self.severity,
            )

        return self._build_result(
            primary_dt, dependent_dt, primary_value, dependent_value
        )

    def _evaluate_number(self, primary_value: str, dependent_value: str) -> RuleResult:
        primary_num = _parse_number(primary_value)
        if primary_num is None:
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"primary value [{primary_value}] could not be parsed as a number",
                severity=self.severity,
            )

        dependent_num = _parse_number(dependent_value)
        if dependent_num is None:
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"dependent value [{dependent_value}] could not be parsed as a number",
                severity=self.severity,
            )

        return self._build_result(
            primary_num, dependent_num, primary_value, dependent_value
        )

    def _evaluate_string(self, primary_value: str, dependent_value: str) -> RuleResult:
        return self._build_result(
            primary_value, dependent_value, primary_value, dependent_value
        )

    def _build_result(
        self,
        lhs: Comparable,
        rhs: Comparable,
        primary_display: str,
        dependent_display: str,
    ) -> RuleResult:
        if _compare(lhs, rhs, self.relation):
            return RuleResult.passed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=(
                    f"[{self.primary_fact_type}={primary_display}] "
                    f"{self.relation.value} "
                    f"[{self.dependent_fact_type}={dependent_display}]"
                ),
            )

        return RuleResult.failed_result(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            message=(
                f"[{self.primary_fact_type}={primary_display}] "
                f"violates {self.relation.value} "
                f"[{self.dependent_fact_type}={dependent_display}]"
            ),
            severity=self.severity,
        )
