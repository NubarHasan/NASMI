from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_candidate_fact_id,
    is_valid_candidate_fact_id,
    is_valid_entity_id,
    is_valid_evidence_id,
    is_valid_source_id,
)
from core.types import (
    CandidateFactId,
    ConfidenceScore,
    EntityId,
    EvidenceId,
    SourceId,
)


@dataclass(frozen=True)
class CandidateFact:
    candidate_fact_id: CandidateFactId
    entity_id: EntityId
    source_id: SourceId
    fact_type: str
    raw_value: str
    normalized_value: str
    confidence: ConfidenceScore
    evidence_ids: tuple[EvidenceId, ...]
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_candidate_fact_id(self.candidate_fact_id),
            f"Invalid CandidateFactId: [{self.candidate_fact_id}]",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"Invalid EntityId: [{self.entity_id}]",
        )
        require(
            is_valid_source_id(self.source_id),
            f"Invalid SourceId: [{self.source_id}]",
        )
        require(
            bool(self.fact_type.strip()),
            "fact_type must not be empty",
        )
        require(
            bool(self.raw_value.strip()),
            "raw_value must not be empty",
        )
        require(
            bool(self.normalized_value.strip()),
            "normalized_value must not be empty",
        )
        require(
            0.0 <= self.confidence <= 1.0,
            f"confidence must be between 0.0 and 1.0, got [{self.confidence}]",
        )
        require(
            len(self.evidence_ids) > 0,
            "evidence_ids must not be empty",
        )
        require(
            all(is_valid_evidence_id(e) for e in self.evidence_ids),
            "one or more evidence_ids are invalid",
        )
        require(
            isinstance(self.created_at, datetime),
            "created_at must be a datetime instance",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )

    def with_metadata(self, key: str, value: Any) -> CandidateFact:
        return CandidateFact(
            **{**self.__dict__, "metadata": {**self.metadata, key: value}},
        )

    def with_confidence(self, confidence: ConfidenceScore) -> CandidateFact:
        require(
            0.0 <= confidence <= 1.0,
            f"confidence must be between 0.0 and 1.0, got [{confidence}]",
        )
        return CandidateFact(**{**self.__dict__, "confidence": confidence})

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.9

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @classmethod
    def create(
        cls,
        entity_id: EntityId,
        source_id: SourceId,
        fact_type: str,
        raw_value: str,
        normalized_value: str,
        confidence: ConfidenceScore,
        evidence_ids: tuple[EvidenceId, ...],
        created_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> CandidateFact:
        return cls(
            candidate_fact_id=generate_candidate_fact_id(),
            entity_id=entity_id,
            source_id=source_id,
            fact_type=fact_type,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=confidence,
            evidence_ids=evidence_ids,
            created_at=created_at,
            metadata=dict(metadata) if metadata is not None else {},
        )
