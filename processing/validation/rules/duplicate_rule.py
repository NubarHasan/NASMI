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
class DuplicateRule:

    rule_id: str
    rule_name: str
    fact_type: str
    severity: ValidationSeverity = ValidationSeverity.ERROR

    def __post_init__(self) -> None:
        require(bool(self.rule_id.strip()), "rule_id must not be blank")
        require(bool(self.rule_name.strip()), "rule_name must not be blank")
        require(bool(self.fact_type.strip()), "fact_type must not be blank")
        require(
            isinstance(self.severity, ValidationSeverity),
            "severity must be a ValidationSeverity",
        )

    def evaluate(
        self,
        candidate_fact: CandidateFact,
        context: ValidationContext,
    ) -> RuleResult:
        if candidate_fact.fact_type != self.fact_type:
            return RuleResult.passed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"fact_type [{candidate_fact.fact_type}] not targeted by this rule",
            )

        accepted = context.accepted_for_field(self.fact_type)

        for fact in accepted:
            if fact.canonical_value == candidate_fact.normalized_value:
                return RuleResult.failed_result(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"duplicate value [{candidate_fact.normalized_value}] "
                        f"already exists for [{self.fact_type}]"
                    ),
                    severity=self.severity,
                )

        return RuleResult.passed_result(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            message=(
                f"no duplicate found for value [{candidate_fact.normalized_value}] "
                f"in [{self.fact_type}]"
            ),
        )
