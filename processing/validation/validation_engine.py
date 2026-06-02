from __future__ import annotations

from core.guards import require
from processing.extraction.candidate_fact import CandidateFact
from processing.validation.validation_context import ValidationContext
from processing.validation.validation_report import ValidationReport
from processing.validation.validation_rule import ValidationRule


class ValidationEngine:

    def __init__(
        self,
        rules: tuple[ValidationRule, ...],
    ) -> None:
        require(isinstance(rules, tuple), "rules must be a tuple")
        require(
            all(isinstance(r, ValidationRule) for r in rules),
            "all rules must implement ValidationRule",
        )
        require(len(rules) > 0, "rules must not be empty")
        rule_ids = [r.rule_id for r in rules]
        require(
            len(rule_ids) == len(set(rule_ids)),
            "all rules must have unique rule_id",
        )
        self._rules = rules

    @property
    def rules(self) -> tuple[ValidationRule, ...]:
        return self._rules

    def validate(
        self,
        candidate_fact: CandidateFact,
        context: ValidationContext,
    ) -> ValidationReport:
        require(
            isinstance(candidate_fact, CandidateFact),
            "candidate_fact must be a CandidateFact instance",
        )
        require(
            isinstance(context, ValidationContext),
            "context must be a ValidationContext instance",
        )
        require(
            candidate_fact.entity_id == context.entity.entity_id,
            "candidate_fact.entity_id must match context.entity.entity_id",
        )
        results = tuple(rule.evaluate(candidate_fact, context) for rule in self._rules)
        return ValidationReport.create(
            candidate_id=candidate_fact.candidate_fact_id,
            entity_id=candidate_fact.entity_id,
            field_name=candidate_fact.fact_type,
            results=results,
        )
