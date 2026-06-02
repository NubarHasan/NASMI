from __future__ import annotations

from typing import Protocol, runtime_checkable

from extraction.candidate_fact import CandidateFact

from processing.validation.validation_context import ValidationContext
from processing.validation.validation_report import RuleResult


@runtime_checkable
class ValidationRule(Protocol):

    @property
    def rule_id(self) -> str: ...

    @property
    def rule_name(self) -> str: ...

    def evaluate(
        self,
        candidate_fact: CandidateFact,
        context: ValidationContext,
    ) -> RuleResult: ...
