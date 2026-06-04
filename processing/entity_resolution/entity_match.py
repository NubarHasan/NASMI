from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.types import CandidateFactId, SpanId


class MatchStrategy(StrEnum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    IDENTIFIER = "identifier"
    DATE = "date"


class MatchSignal(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"

    @classmethod
    def from_confidence(cls, confidence: float) -> MatchSignal:
        require(
            0.0 <= confidence <= 1.0,
            f"confidence must be in [0.0, 1.0], got [{confidence}]",
        )
        if confidence >= 0.90:
            return cls.STRONG
        if confidence >= 0.70:
            return cls.MODERATE
        if confidence >= 0.40:
            return cls.WEAK
        return cls.UNKNOWN


@dataclass(frozen=True)
class EntityMatch:
    fact_type: str
    value_a: str
    value_b: str
    fact_id_a: CandidateFactId
    fact_id_b: CandidateFactId
    strategy: MatchStrategy
    confidence: float
    signal: MatchSignal
    span_ids_a: tuple[SpanId, ...] = field(default_factory=tuple)
    span_ids_b: tuple[SpanId, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            isinstance(self.fact_type, str) and bool(self.fact_type.strip()),
            "fact_type must be a non-empty string",
        )
        require(isinstance(self.value_a, str), "value_a must be a string")
        require(isinstance(self.value_b, str), "value_b must be a string")
        require(
            isinstance(self.fact_id_a, str) and bool(self.fact_id_a.strip()),
            "fact_id_a must be a non-empty string",
        )
        require(
            isinstance(self.fact_id_b, str) and bool(self.fact_id_b.strip()),
            "fact_id_b must be a non-empty string",
        )
        require(
            self.fact_id_a != self.fact_id_b,
            "fact_id_a and fact_id_b must be different facts",
        )
        require(
            isinstance(self.strategy, MatchStrategy),
            f"strategy must be MatchStrategy, got [{type(self.strategy)}]",
        )
        require(
            isinstance(self.confidence, float) and 0.0 <= self.confidence <= 1.0,
            f"confidence must be float in [0.0, 1.0], got [{self.confidence}]",
        )
        require(
            isinstance(self.signal, MatchSignal),
            f"signal must be MatchSignal, got [{type(self.signal)}]",
        )
        require(isinstance(self.span_ids_a, tuple), "span_ids_a must be a tuple")
        require(isinstance(self.span_ids_b, tuple), "span_ids_b must be a tuple")
        require(isinstance(self.metadata, Mapping), "metadata must be a Mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def is_strong(self) -> bool:
        return self.signal == MatchSignal.STRONG

    @property
    def is_conflict(self) -> bool:
        return self.signal == MatchSignal.CONFLICT

    @property
    def is_unknown(self) -> bool:
        return self.signal == MatchSignal.UNKNOWN

    @property
    def values_are_identical(self) -> bool:
        return self.value_a == self.value_b

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_type": self.fact_type,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "fact_id_a": self.fact_id_a,
            "fact_id_b": self.fact_id_b,
            "strategy": str(self.strategy),
            "confidence": self.confidence,
            "signal": str(self.signal),
            "span_ids_a": list(self.span_ids_a),
            "span_ids_b": list(self.span_ids_b),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityMatch:
        confidence = float(data["confidence"])
        return cls(
            fact_type=data["fact_type"],
            value_a=data["value_a"],
            value_b=data["value_b"],
            fact_id_a=CandidateFactId(data["fact_id_a"]),
            fact_id_b=CandidateFactId(data["fact_id_b"]),
            strategy=MatchStrategy(data["strategy"]),
            confidence=confidence,
            signal=MatchSignal(data["signal"]),
            span_ids_a=tuple(SpanId(s) for s in data.get("span_ids_a", [])),
            span_ids_b=tuple(SpanId(s) for s in data.get("span_ids_b", [])),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def create(
        cls,
        fact_type: str,
        value_a: str,
        value_b: str,
        fact_id_a: CandidateFactId,
        fact_id_b: CandidateFactId,
        strategy: MatchStrategy,
        confidence: float,
        signal: MatchSignal | None = None,
        span_ids_a: tuple[SpanId, ...] = (),
        span_ids_b: tuple[SpanId, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> EntityMatch:
        return cls(
            fact_type=fact_type,
            value_a=value_a,
            value_b=value_b,
            fact_id_a=fact_id_a,
            fact_id_b=fact_id_b,
            strategy=strategy,
            confidence=confidence,
            signal=(
                signal
                if signal is not None
                else MatchSignal.from_confidence(confidence)
            ),
            span_ids_a=span_ids_a,
            span_ids_b=span_ids_b,
            metadata=dict(metadata) if metadata is not None else {},
        )


@dataclass(frozen=True)
class EntityMatchBundle:
    matches: tuple[EntityMatch, ...]
    overall_score: float
    resolved_entity_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.matches, tuple), "matches must be a tuple")
        require(
            all(isinstance(m, EntityMatch) for m in self.matches),
            "all matches must be EntityMatch instances",
        )
        require(
            isinstance(self.overall_score, float) and 0.0 <= self.overall_score <= 1.0,
            f"overall_score must be float in [0.0, 1.0], got [{self.overall_score}]",
        )
        require(
            self.resolved_entity_id is None
            or (
                isinstance(self.resolved_entity_id, str)
                and bool(self.resolved_entity_id.strip())
            ),
            "resolved_entity_id must be a non-empty string or None",
        )
        require(isinstance(self.metadata, Mapping), "metadata must be a Mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def overall_signal(self) -> MatchSignal:
        return MatchSignal.from_confidence(self.overall_score)

    @property
    def has_conflicts(self) -> bool:
        return any(m.is_conflict for m in self.matches)

    @property
    def is_resolved(self) -> bool:
        return self.resolved_entity_id is not None

    @property
    def conflict_matches(self) -> tuple[EntityMatch, ...]:
        return tuple(m for m in self.matches if m.is_conflict)

    @property
    def strong_matches(self) -> tuple[EntityMatch, ...]:
        return tuple(m for m in self.matches if m.is_strong)

    @property
    def match_count(self) -> int:
        return len(self.matches)

    def matches_for_fact_type(self, fact_type: str) -> tuple[EntityMatch, ...]:
        return tuple(m for m in self.matches if m.fact_type == fact_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "overall_score": self.overall_score,
            "overall_signal": str(self.overall_signal),
            "resolved_entity_id": self.resolved_entity_id,
            "has_conflicts": self.has_conflicts,
            "is_resolved": self.is_resolved,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityMatchBundle:
        return cls(
            matches=tuple(EntityMatch.from_dict(m) for m in data.get("matches", [])),
            overall_score=float(data["overall_score"]),
            resolved_entity_id=data.get("resolved_entity_id"),
            metadata=dict(data.get("metadata", {})),
        )
