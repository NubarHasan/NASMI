from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FactStatus(StrEnum):
    CONFIRMED = "confirmed"
    CONFLICTED = "conflicted"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class FactSource:
    document_id: str
    document_type: str
    excerpt: str
    confidence: float | None = None


@dataclass(frozen=True)
class ProfileFact:
    fact_id: str
    field: str
    value: str
    status: FactStatus
    sources: tuple[FactSource, ...] = ()


@dataclass(frozen=True)
class ProfileSnapshot:
    entity_id: str
    entity_name: str
    facts: tuple[ProfileFact, ...] = ()
    confidence: float | None = None
