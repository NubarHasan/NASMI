from __future__ import annotations

import re
from dataclasses import dataclass

from core.guards import require
from processing.extraction.candidate_fact import CandidateFact
from processing.validation.validation_context import ValidationContext
from processing.validation.validation_report import (
    RuleResult,
    ValidationSeverity,
)


@dataclass(frozen=True)
class FormatRule:

    rule_id: str
    rule_name: str
    fact_type: str
    pattern: str
    severity: ValidationSeverity = ValidationSeverity.ERROR

    def __post_init__(self) -> None:
        require(bool(self.rule_id.strip()), "rule_id must not be blank")
        require(bool(self.rule_name.strip()), "rule_name must not be blank")
        require(bool(self.fact_type.strip()), "fact_type must not be blank")
        require(bool(self.pattern.strip()), "pattern must not be blank")
        require(
            isinstance(self.severity, ValidationSeverity),
            "severity must be a ValidationSeverity",
        )
        try:
            re.compile(self.pattern)
        except re.error:
            require(False, f"invalid regex pattern [{self.pattern}]")

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

        if re.fullmatch(self.pattern, value):
            return RuleResult.passed_result(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                message=f"value matches format for [{self.fact_type}]",
            )

        return RuleResult.failed_result(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            message=f"[{value}] does not match expected format for [{self.fact_type}]",
            severity=self.severity,
        )
