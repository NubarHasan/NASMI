from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_candidate_fact_id,
    is_valid_candidate_fact_id,
    is_valid_document_id,
    is_valid_entity_id,
    is_valid_source_id,
    is_valid_span_id,
)
from core.time import utcnow
from core.types import (
    CandidateFactId,
    ConfidenceScore,
    DocumentId,
    EntityId,
    SourceId,
    SpanId,
)

_MIN_CONFIDENCE: float = 0.0
_MAX_CONFIDENCE: float = 1.0


@dataclass(frozen=True)
class CandidateFact:
    candidate_fact_id: CandidateFactId
    document_id: DocumentId
    source_id: SourceId
    entity_id: EntityId
    fact_type: str
    source_stage: str
    raw_value: str
    normalized_value: str
    confidence: ConfidenceScore
    span_ids: tuple[SpanId, ...]
    extracted_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_candidate_fact_id(self.candidate_fact_id),
            f"Invalid CandidateFactId: [{self.candidate_fact_id}]",
        )
        require(
            is_valid_document_id(self.document_id),
            f"Invalid DocumentId: [{self.document_id}]",
        )
        require(
            is_valid_source_id(self.source_id),
            f"Invalid SourceId: [{self.source_id}]",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"Invalid EntityId: [{self.entity_id}]",
        )
        require(
            isinstance(self.fact_type, str) and bool(self.fact_type.strip()),
            "fact_type must be a non-empty string",
        )
        require(
            isinstance(self.source_stage, str) and bool(self.source_stage.strip()),
            "source_stage must be a non-empty string",
        )
        require(
            isinstance(self.raw_value, str) and bool(self.raw_value.strip()),
            "raw_value must be a non-empty string",
        )
        require(
            isinstance(self.normalized_value, str)
            and bool(self.normalized_value.strip()),
            "normalized_value must be a non-empty string",
        )
        require(
            isinstance(self.confidence, (int, float))
            and _MIN_CONFIDENCE <= self.confidence <= _MAX_CONFIDENCE,
            f"confidence must be in [0.0, 1.0], got [{self.confidence}]",
        )
        require(
            isinstance(self.span_ids, tuple) and len(self.span_ids) > 0,
            "span_ids must be a non-empty tuple",
        )
        require(
            all(is_valid_span_id(s) for s in self.span_ids),
            "one or more span_ids are invalid",
        )
        require(
            isinstance(self.extracted_at, datetime),
            "extracted_at must be a datetime instance",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dict",
        )

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.9

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def span_count(self) -> int:
        return len(self.span_ids)

    @property
    def has_multiple_spans(self) -> bool:
        return len(self.span_ids) > 1

    def with_confidence(self, confidence: ConfidenceScore) -> CandidateFact:
        require(
            isinstance(confidence, (int, float))
            and _MIN_CONFIDENCE <= confidence <= _MAX_CONFIDENCE,
            f"confidence must be in [0.0, 1.0], got [{confidence}]",
        )
        return CandidateFact(
            candidate_fact_id=self.candidate_fact_id,
            document_id=self.document_id,
            source_id=self.source_id,
            entity_id=self.entity_id,
            fact_type=self.fact_type,
            source_stage=self.source_stage,
            raw_value=self.raw_value,
            normalized_value=self.normalized_value,
            confidence=confidence,
            span_ids=self.span_ids,
            extracted_at=self.extracted_at,
            metadata=dict(self.metadata),
        )

    def with_metadata(self, key: str, value: Any) -> CandidateFact:
        require(
            isinstance(key, str) and bool(key.strip()),
            "key must be a non-empty string",
        )
        return CandidateFact(
            candidate_fact_id=self.candidate_fact_id,
            document_id=self.document_id,
            source_id=self.source_id,
            entity_id=self.entity_id,
            fact_type=self.fact_type,
            source_stage=self.source_stage,
            raw_value=self.raw_value,
            normalized_value=self.normalized_value,
            confidence=self.confidence,
            span_ids=self.span_ids,
            extracted_at=self.extracted_at,
            metadata={**self.metadata, key: value},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_fact_id": self.candidate_fact_id,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "entity_id": self.entity_id,
            "fact_type": self.fact_type,
            "source_stage": self.source_stage,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "confidence": self.confidence,
            "span_ids": list(self.span_ids),
            "extracted_at": self.extracted_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateFact:
        return cls(
            candidate_fact_id=CandidateFactId(data["candidate_fact_id"]),
            document_id=DocumentId(data["document_id"]),
            source_id=SourceId(data["source_id"]),
            entity_id=EntityId(data["entity_id"]),
            fact_type=data["fact_type"],
            source_stage=data["source_stage"],
            raw_value=data["raw_value"],
            normalized_value=data["normalized_value"],
            confidence=float(data["confidence"]),
            span_ids=tuple(SpanId(s) for s in data["span_ids"]),
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def create(
        cls,
        document_id: DocumentId,
        source_id: SourceId,
        entity_id: EntityId,
        fact_type: str,
        source_stage: str,
        raw_value: str,
        normalized_value: str,
        confidence: ConfidenceScore,
        span_ids: tuple[SpanId, ...],
        metadata: dict[str, Any] | None = None,
    ) -> CandidateFact:
        return cls(
            candidate_fact_id=generate_candidate_fact_id(),
            document_id=document_id,
            source_id=source_id,
            entity_id=entity_id,
            fact_type=fact_type,
            source_stage=source_stage,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=confidence,
            span_ids=span_ids,
            extracted_at=utcnow(),
            metadata=dict(metadata) if metadata is not None else {},
        )
