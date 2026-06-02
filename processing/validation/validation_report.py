from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from core.guards import require
from core.identifiers import (
    generate_validation_report_id,
    is_valid_candidate_fact_id,
    is_valid_entity_id,
    is_valid_validation_report_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import CandidateFactId, EntityId, ValidationReportId


class ValidationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ValidationStatus(StrEnum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    rule_name: str
    passed: bool
    severity: ValidationSeverity
    message: str

    def __post_init__(self) -> None:
        require(bool(self.rule_id.strip()), "rule_id must not be blank")
        require(bool(self.rule_name.strip()), "rule_name must not be blank")
        require(bool(self.message.strip()), "message must not be blank")
        require(
            isinstance(self.severity, ValidationSeverity),
            "severity must be a ValidationSeverity",
        )

    @classmethod
    def passed_result(
        cls,
        rule_id: str,
        rule_name: str,
        message: str = "OK",
        severity: ValidationSeverity = ValidationSeverity.INFO,
    ) -> RuleResult:
        return cls(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            severity=severity,
            message=message,
        )

    @classmethod
    def failed_result(
        cls,
        rule_id: str,
        rule_name: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> RuleResult:
        require(bool(message.strip()), "failure message must not be blank")
        return cls(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=False,
            severity=severity,
            message=message,
        )


@dataclass(frozen=True)
class ValidationReport:
    report_id: ValidationReportId
    candidate_id: CandidateFactId
    entity_id: EntityId
    field_name: str
    results: tuple[RuleResult, ...]
    status: ValidationStatus
    validated_at: str

    def __post_init__(self) -> None:
        require(
            is_valid_validation_report_id(self.report_id),
            "invalid report_id",
        )
        require(
            is_valid_candidate_fact_id(self.candidate_id),
            "invalid candidate_id",
        )
        require(is_valid_entity_id(self.entity_id), "invalid entity_id")
        require(bool(self.field_name.strip()), "field_name must not be blank")
        require(
            isinstance(self.results, tuple),
            "results must be a tuple",
        )
        require(
            all(isinstance(r, RuleResult) for r in self.results),
            "results must contain only RuleResult instances",
        )
        require(
            isinstance(self.status, ValidationStatus),
            "status must be a ValidationStatus",
        )
        require(
            is_valid_timestamp(self.validated_at),
            "invalid validated_at",
        )

    @classmethod
    def create(
        cls,
        candidate_id: CandidateFactId,
        entity_id: EntityId,
        field_name: str,
        results: tuple[RuleResult, ...],
    ) -> ValidationReport:
        require(
            is_valid_candidate_fact_id(candidate_id),
            "invalid candidate_id",
        )
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(bool(field_name.strip()), "field_name must not be blank")
        require(
            isinstance(results, tuple),
            "results must be a tuple",
        )
        require(
            all(isinstance(r, RuleResult) for r in results),
            "results must contain only RuleResult instances",
        )

        return cls(
            report_id=generate_validation_report_id(),
            candidate_id=candidate_id,
            entity_id=entity_id,
            field_name=field_name,
            results=tuple(results),
            status=_derive_status(results),
            validated_at=utcnow_iso(),
        )

    def has_errors(self) -> bool:
        return any(
            not r.passed and r.severity == ValidationSeverity.ERROR
            for r in self.results
        )

    def has_warnings(self) -> bool:
        return any(
            not r.passed and r.severity == ValidationSeverity.WARNING
            for r in self.results
        )

    def errors(self) -> tuple[RuleResult, ...]:
        return tuple(
            r
            for r in self.results
            if not r.passed and r.severity == ValidationSeverity.ERROR
        )

    def warnings(self) -> tuple[RuleResult, ...]:
        return tuple(
            r
            for r in self.results
            if not r.passed and r.severity == ValidationSeverity.WARNING
        )

    def passed_rules(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.results if r.passed)

    def highest_severity(self) -> ValidationSeverity:
        _rank = {
            ValidationSeverity.INFO: 0,
            ValidationSeverity.WARNING: 1,
            ValidationSeverity.ERROR: 2,
        }
        failed = [r for r in self.results if not r.passed]
        if not failed:
            return ValidationSeverity.INFO
        return max(failed, key=lambda r: _rank[r.severity]).severity

    def is_passable(self) -> bool:
        return self.status in (ValidationStatus.PASSED, ValidationStatus.WARNING)


def _derive_status(results: tuple[RuleResult, ...]) -> ValidationStatus:
    if not results:
        return ValidationStatus.PASSED
    if any(not r.passed and r.severity == ValidationSeverity.ERROR for r in results):
        return ValidationStatus.FAILED
    if any(not r.passed and r.severity == ValidationSeverity.WARNING for r in results):
        return ValidationStatus.WARNING
    return ValidationStatus.PASSED
