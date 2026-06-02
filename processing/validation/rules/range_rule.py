from __future__ import annotations

from dataclasses import dataclass

from core.guards import require
from processing.extraction.candidate_fact import CandidateFact
from processing.validation.validation_context import ValidationContext
from processing.validation.validation_report import (
    RuleResult,
    ValidationSeverity,
)


@dataclass(frozen=True)
class RangeRule:

    rule_id: str
    rule_name: str
    fact_type: str
    minimum: float | int | None = None
    maximum: float | int | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR

    def __post_init__(self) -> None:
        require(bool(self.rule_id.strip()), "rule_id must not be blank")
        require(bool(self.rule_name.strip()), "rule_name must not be blank")
        require(bool(self.fact_type.strip()), "fact_type must not be blank")
        require(
            isinstance(self.severity, ValidationSeverity),
            "severity must be a ValidationSeverity",
        )
        require(
            self.minimum is not None or self.maximum is not None,
            "at least one boundary must be provided",
        )
        if self.minimum is not None:
            require(
                isinstance(self.minimum, (int, float)),
                "minimum must be numeric",
            )
        if self.maximum is not None:
            require(
                isinstance(self.maximum, (int, float)),
                "maximum must be numeric",
            )
        require(
            self.minimum is None
            or self.maximum is None
            or self.minimum <= self.maximum,
            "minimum must be less than or equal to maximum",
        )

    def evaluate(
        self,
        candidate_fact: CandidateFact,
        context: ValidationContext,  # noqa: ARG002
    ) -> RuleResult:
        if candidate_fact.fact_type != self.fact_type:
            return RuleResult.passed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"fact_type [{candidate_fact.fact_type}] not targeted by this rule",
            )

        value = candidate_fact.normalized_value

        try:
            numeric = float(value)
        except (ValueError, TypeError):
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"value [{value}] is not numeric",
                severity=self.severity,
            )

        if self.minimum is not None and numeric < self.minimum:
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"value [{value}] is below minimum [{self.minimum}] for [{self.fact_type}]",
                severity=self.severity,
            )

        if self.maximum is not None and numeric > self.maximum:
            return RuleResult.failed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"value [{value}] exceeds maximum [{self.maximum}] for [{self.fact_type}]",
                severity=self.severity,
            )

        return RuleResult.passed_result(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            message=f"value [{value}] is within range for [{self.fact_type}]",
        )
