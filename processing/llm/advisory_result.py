from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EXPIRY_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "expiry_date",
        "DOCUMENT_DATE",
        "document_date",
        "passport_expiry",
        "id_expiry",
        "valid_until",
        "gueltig_bis",
        "ablaufdatum",
    }
)

SUPPORTED_LOCALES: frozenset[str] = frozenset({"en", "de", "ar"})


@dataclass(frozen=True)
class AdvisoryItem:
    entity_id: str
    display_name: str
    field_name: str
    expiry_date: str  # ISO format: YYYY-MM-DD
    days_remaining: int
    severity: str  # "critical" | "warning" | "info"
    locale: str
    message: str  # translated human-readable message
    suggestion: str  # translated suggestion
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return self.days_remaining < 0

    @property
    def is_critical(self) -> bool:
        return self.severity == "critical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "field_name": self.field_name,
            "expiry_date": self.expiry_date,
            "days_remaining": self.days_remaining,
            "severity": self.severity,
            "locale": self.locale,
            "message": self.message,
            "suggestion": self.suggestion,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AdvisoryResult:
    items: tuple[AdvisoryItem, ...]
    locale: str
    llm_summary: str  # LLM-generated overall summary
    llm_failure: str | None  # None if LLM succeeded

    @property
    def has_critical(self) -> bool:
        return any(i.is_critical for i in self.items)

    @property
    def critical_items(self) -> tuple[AdvisoryItem, ...]:
        return tuple(i for i in self.items if i.severity == "critical")

    @property
    def warning_items(self) -> tuple[AdvisoryItem, ...]:
        return tuple(i for i in self.items if i.severity == "warning")

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def llm_available(self) -> bool:
        return self.llm_failure is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "locale": self.locale,
            "llm_summary": self.llm_summary,
            "llm_failure": self.llm_failure,
            "has_critical": self.has_critical,
            "total_count": self.total_count,
        }
