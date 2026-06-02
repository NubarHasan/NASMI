from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.guards import require
from processing.extraction.candidate_fact import CandidateFact
from processing.validation.validation_context import ValidationContext
from processing.validation.validation_report import (
    RuleResult,
    ValidationSeverity,
)


@dataclass(frozen=True)
class DateRule:

    rule_id: str
    rule_name: str
    fact_type: str
    accepted_formats: tuple[str, ...]
    severity: ValidationSeverity = ValidationSeverity.ERROR

    def __post_init__(self) -> None:
        require(bool(self.rule_id.strip()), "rule_id must not be blank")
        require(bool(self.rule_name.strip()), "rule_name must not be blank")
        require(bool(self.fact_type.strip()), "fact_type must not be blank")
        require(
            isinstance(self.accepted_formats, tuple),
            "accepted_formats must be a tuple",
        )
        require(
            len(self.accepted_formats) > 0,
            "accepted_formats must not be empty",
        )
        require(
            all(isinstance(f, str) and bool(f.strip()) for f in self.accepted_formats),
            "each accepted_format must be a non-blank string",
        )
        require(
            len(set(self.accepted_formats)) == len(self.accepted_formats),
            "accepted_formats must not contain duplicates",
        )
        require(
            isinstance(self.severity, ValidationSeverity),
            "severity must be a ValidationSeverity",
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

        for fmt in self.accepted_formats:
            try:
                datetime.strptime(value, fmt)
                return RuleResult.passed_result(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=f"value [{value}] matches date format [{fmt}] for [{self.fact_type}]",
                )
            except (ValueError, TypeError):
                continue

        accepted = ", ".join(self.accepted_formats)
        return RuleResult.failed_result(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            message=f"value [{value}] does not match any accepted date format [{accepted}] for [{self.fact_type}]",
            severity=self.severity,
        )
