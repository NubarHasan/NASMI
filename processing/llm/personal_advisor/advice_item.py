from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from processing.llm.personal_advisor.advice_category import AdviceCategory


@dataclass(frozen=True)
class AdviceItem:
    category: AdviceCategory
    severity: str  # "critical" | "warning" | "info"
    title: str
    body: str
    suggestion: str
    entity_id: str | None = None
    locale: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        return self.severity == "critical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "suggestion": self.suggestion,
            "entity_id": self.entity_id,
            "locale": self.locale,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PersonalAdvisoryResult:
    entity_id: str
    display_name: str
    locale: str
    items: tuple[AdviceItem, ...]
    llm_summary: str
    llm_failure: str | None

    @property
    def has_critical(self) -> bool:
        return any(i.is_critical for i in self.items)

    @property
    def by_category(self) -> dict[AdviceCategory, tuple[AdviceItem, ...]]:
        result: dict[AdviceCategory, list[AdviceItem]] = {}
        for item in self.items:
            result.setdefault(item.category, []).append(item)
        return {k: tuple(v) for k, v in result.items()}

    @property
    def critical_items(self) -> tuple[AdviceItem, ...]:
        return tuple(i for i in self.items if i.severity == "critical")

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "locale": self.locale,
            "items": [i.to_dict() for i in self.items],
            "llm_summary": self.llm_summary,
            "llm_failure": self.llm_failure,
            "has_critical": self.has_critical,
        }
