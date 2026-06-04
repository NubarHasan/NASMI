from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.identifiers import generate_entity_resolution_result_id
from core.time import parse_timestamp, utcnow
from core.types import (
    CandidateFactId,
    EntityId,
    EntityResolutionResultId,
)
from processing.entity_resolution.entity_match import EntityMatchBundle, MatchSignal


@dataclass(frozen=True)
class EntityResolutionResult:
    result_id: EntityResolutionResultId
    resolved_entity_id: EntityId
    candidate_fact_ids: tuple[CandidateFactId, ...]
    bundle: EntityMatchBundle
    canonical_values: Mapping[str, str]
    conflict_fact_types: tuple[str, ...]
    conflict_details: Mapping[str, tuple[CandidateFactId, ...]]
    resolution_confidence: float
    created_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            isinstance(self.result_id, str) and bool(self.result_id.strip()),
            "result_id must be a non-empty string",
        )
        require(
            isinstance(self.resolved_entity_id, str)
            and bool(self.resolved_entity_id.strip()),
            "resolved_entity_id must be a non-empty string",
        )
        require(
            isinstance(self.candidate_fact_ids, tuple)
            and len(self.candidate_fact_ids) >= 1,
            "candidate_fact_ids must be a non-empty tuple",
        )
        require(
            all(
                isinstance(f, str) and bool(f.strip()) for f in self.candidate_fact_ids
            ),
            "all candidate_fact_ids must be non-empty strings",
        )
        require(
            len(set(self.candidate_fact_ids)) == len(self.candidate_fact_ids),
            "candidate_fact_ids must be unique",
        )
        require(
            isinstance(self.bundle, EntityMatchBundle),
            "bundle must be an EntityMatchBundle instance",
        )
        require(
            isinstance(self.canonical_values, Mapping),
            "canonical_values must be a Mapping",
        )
        require(
            all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in self.canonical_values.items()
            ),
            "canonical_values must be Mapping[str, str]",
        )
        require(
            isinstance(self.conflict_fact_types, tuple),
            "conflict_fact_types must be a tuple",
        )
        require(
            all(
                isinstance(t, str) and bool(t.strip()) for t in self.conflict_fact_types
            ),
            "all conflict_fact_types must be non-empty strings",
        )
        require(
            isinstance(self.conflict_details, Mapping),
            "conflict_details must be a Mapping",
        )
        require(
            all(
                isinstance(k, str)
                and isinstance(v, tuple)
                and len(v) >= 2
                and all(isinstance(fid, str) and bool(fid.strip()) for fid in v)
                for k, v in self.conflict_details.items()
            ),
            "conflict_details must be Mapping[str, tuple[CandidateFactId, ...]] "
            "with at least 2 ids per field",
        )
        require(
            frozenset(self.conflict_details.keys())
            == frozenset(self.conflict_fact_types),
            "conflict_details keys must match conflict_fact_types exactly",
        )
        require(
            isinstance(self.resolution_confidence, float)
            and 0.0 <= self.resolution_confidence <= 1.0,
            f"resolution_confidence must be float in [0.0, 1.0], "
            f"got [{self.resolution_confidence}]",
        )
        require(
            isinstance(self.created_at, datetime),
            "created_at must be a datetime instance",
        )
        require(
            isinstance(self.metadata, Mapping),
            "metadata must be a Mapping",
        )
        object.__setattr__(
            self, "canonical_values", MappingProxyType(dict(self.canonical_values))
        )
        object.__setattr__(
            self,
            "conflict_details",
            MappingProxyType({k: tuple(v) for k, v in self.conflict_details.items()}),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflict_fact_types) > 0

    @property
    def is_high_confidence(self) -> bool:
        return self.resolution_confidence >= 0.90

    @property
    def is_low_confidence(self) -> bool:
        return self.resolution_confidence < 0.50

    @property
    def fact_count(self) -> int:
        return len(self.candidate_fact_ids)

    def canonical_value_for(self, fact_type: str) -> str | None:
        return self.canonical_values.get(fact_type)

    def has_canonical(self, fact_type: str) -> bool:
        return fact_type in self.canonical_values

    def competing_candidate_ids(self, fact_type: str) -> tuple[CandidateFactId, ...]:
        return self.conflict_details.get(fact_type, ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "resolved_entity_id": self.resolved_entity_id,
            "candidate_fact_ids": list(self.candidate_fact_ids),
            "bundle": self.bundle.to_dict(),
            "canonical_values": dict(self.canonical_values),
            "conflict_fact_types": list(self.conflict_fact_types),
            "conflict_details": {k: list(v) for k, v in self.conflict_details.items()},
            "resolution_confidence": self.resolution_confidence,
            "has_conflicts": self.has_conflicts,
            "is_high_confidence": self.is_high_confidence,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityResolutionResult:
        return cls(
            result_id=EntityResolutionResultId(data["result_id"]),
            resolved_entity_id=EntityId(data["resolved_entity_id"]),
            candidate_fact_ids=tuple(
                CandidateFactId(f) for f in data["candidate_fact_ids"]
            ),
            bundle=EntityMatchBundle.from_dict(data["bundle"]),
            canonical_values=dict(data.get("canonical_values", {})),
            conflict_fact_types=tuple(data.get("conflict_fact_types", [])),
            conflict_details={
                k: tuple(CandidateFactId(f) for f in v)
                for k, v in data.get("conflict_details", {}).items()
            },
            resolution_confidence=float(data["resolution_confidence"]),
            created_at=parse_timestamp(data["created_at"]),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def create(
        cls,
        resolved_entity_id: EntityId,
        candidate_fact_ids: tuple[CandidateFactId, ...],
        bundle: EntityMatchBundle,
        canonical_values: dict[str, str],
        conflict_fact_types: tuple[str, ...],
        resolution_confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> EntityResolutionResult:
        conflict_details = _extract_conflict_details(bundle, conflict_fact_types)
        return cls(
            result_id=generate_entity_resolution_result_id(),
            resolved_entity_id=resolved_entity_id,
            candidate_fact_ids=candidate_fact_ids,
            bundle=bundle,
            canonical_values=canonical_values,
            conflict_fact_types=conflict_fact_types,
            conflict_details=conflict_details,
            resolution_confidence=resolution_confidence,
            created_at=utcnow(),
            metadata=dict(metadata) if metadata is not None else {},
        )


def _extract_conflict_details(
    bundle: EntityMatchBundle,
    conflict_fact_types: tuple[str, ...],
) -> dict[str, tuple[CandidateFactId, ...]]:
    result: dict[str, tuple[CandidateFactId, ...]] = {}
    conflict_types: frozenset[str] = frozenset(conflict_fact_types)
    for match in bundle.matches:
        if match.signal is not MatchSignal.CONFLICT:
            continue
        if match.fact_type not in conflict_types:
            continue
        existing = set(result.get(match.fact_type, ()))
        existing.add(match.fact_id_a)
        existing.add(match.fact_id_b)
        result[match.fact_type] = tuple(existing)
    return result
