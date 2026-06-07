from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITING = "editing"


class DecisionType(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    EDIT = "edit"


@dataclass(frozen=True)
class ReviewCaseSummary:
    case_id: str
    label: str
    status: ReviewStatus = ReviewStatus.PENDING


@dataclass(frozen=True)
class Suggestion:
    field: str
    value: str
    status: ReviewStatus = ReviewStatus.PENDING


@dataclass(frozen=True)
class Evidence:
    source: str
    excerpt: str
    page: int | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class Conflict:
    conflict_id: str
    field: str
    value_a: str
    value_b: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class ReviewCaseDetail:
    case_id: str
    document_reference: str
    entity_name: str
    status: ReviewStatus
    suggestions: tuple[Suggestion, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    fact_type: str = ""
    raw_value: str = ""
    normalized_value: str = ""
    canonical_field: str = ""
    field_options: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionResult:
    success: bool
    case_id: str = ""
    decision: DecisionType | None = None
    message: str = ""
    error: str = ""
