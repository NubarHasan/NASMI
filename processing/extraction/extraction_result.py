from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_extraction_result_id,
    is_valid_document_id,
    is_valid_extraction_result_id,
    is_valid_source_id,
)
from core.time import utcnow
from core.types import (
    DocumentId,
    EntityId,
    ExtractionResultId,
    ExtractorId,
    SourceId,
)
from processing.extraction.candidate_fact import CandidateFact


@dataclass(frozen=True)
class ExtractionResult:
    extraction_result_id: ExtractionResultId
    document_id: DocumentId
    source_id: SourceId
    extractor_id: ExtractorId
    candidate_facts: tuple[CandidateFact, ...]
    succeeded: bool
    extracted_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_extraction_result_id(self.extraction_result_id),
            f"Invalid ExtractionResultId: [{self.extraction_result_id}]",
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
            isinstance(self.extractor_id, str) and bool(self.extractor_id.strip()),
            "extractor_id must be a non-empty string",
        )
        require(
            isinstance(self.candidate_facts, tuple),
            "candidate_facts must be a tuple",
        )
        require(
            all(isinstance(f, CandidateFact) for f in self.candidate_facts),
            "all candidate_facts must be CandidateFact instances",
        )
        require(
            len(self.candidate_facts)
            == len({f.candidate_fact_id for f in self.candidate_facts}),
            "candidate_fact_id must be unique within ExtractionResult",
        )
        require(
            isinstance(self.succeeded, bool),
            "succeeded must be a bool",
        )
        require(
            not self.succeeded
            or all(f.source_id == self.source_id for f in self.candidate_facts),
            "all candidate_facts must share the same source_id as ExtractionResult",
        )
        require(
            not self.succeeded
            or all(f.document_id == self.document_id for f in self.candidate_facts),
            "all candidate_facts must share the same document_id as ExtractionResult",
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
    def candidate_count(self) -> int:
        return len(self.candidate_facts)

    @property
    def is_empty(self) -> bool:
        return len(self.candidate_facts) == 0

    @property
    def span_count(self) -> int:
        return sum(f.span_count for f in self.candidate_facts)

    @property
    def mean_confidence(self) -> float:
        if not self.candidate_facts:
            return 0.0
        return round(
            sum(f.confidence for f in self.candidate_facts) / len(self.candidate_facts),
            4,
        )

    @property
    def fact_types(self) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for f in self.candidate_facts:
            if f.fact_type not in seen:
                seen.add(f.fact_type)
                result.append(f.fact_type)
        return tuple(result)

    @property
    def unique_fact_type_count(self) -> int:
        return len(self.fact_types)

    @property
    def entity_ids(self) -> tuple[EntityId, ...]:
        seen: set[EntityId] = set()
        result: list[EntityId] = []
        for f in self.candidate_facts:
            if f.entity_id not in seen:
                seen.add(f.entity_id)
                result.append(f.entity_id)
        return tuple(result)

    @property
    def entity_count(self) -> int:
        return len(self.entity_ids)

    @property
    def source_document_count(self) -> int:
        return len({f.document_id for f in self.candidate_facts})

    @property
    def high_confidence_facts(self) -> tuple[CandidateFact, ...]:
        return tuple(f for f in self.candidate_facts if f.is_high_confidence)

    @property
    def low_confidence_facts(self) -> tuple[CandidateFact, ...]:
        return tuple(f for f in self.candidate_facts if f.is_low_confidence)

    @property
    def high_confidence_count(self) -> int:
        return len(self.high_confidence_facts)

    @property
    def low_confidence_count(self) -> int:
        return len(self.low_confidence_facts)

    def facts_by_type(self, fact_type: str) -> tuple[CandidateFact, ...]:
        return tuple(f for f in self.candidate_facts if f.fact_type == fact_type)

    def facts_by_stage(self, source_stage: str) -> tuple[CandidateFact, ...]:
        return tuple(f for f in self.candidate_facts if f.source_stage == source_stage)

    def facts_by_entity(self, entity_id: EntityId) -> tuple[CandidateFact, ...]:
        return tuple(f for f in self.candidate_facts if f.entity_id == entity_id)

    def with_metadata(self, key: str, value: Any) -> ExtractionResult:
        require(
            isinstance(key, str) and bool(key.strip()),
            "key must be a non-empty string",
        )
        return ExtractionResult(
            extraction_result_id=self.extraction_result_id,
            document_id=self.document_id,
            source_id=self.source_id,
            extractor_id=self.extractor_id,
            candidate_facts=self.candidate_facts,
            succeeded=self.succeeded,
            extracted_at=self.extracted_at,
            metadata={**self.metadata, key: value},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "extraction_result_id": self.extraction_result_id,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "extractor_id": self.extractor_id,
            "candidate_facts": [f.to_dict() for f in self.candidate_facts],
            "succeeded": self.succeeded,
            "extracted_at": self.extracted_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionResult:
        return cls(
            extraction_result_id=ExtractionResultId(data["extraction_result_id"]),
            document_id=DocumentId(data["document_id"]),
            source_id=SourceId(data["source_id"]),
            extractor_id=ExtractorId(data["extractor_id"]),
            candidate_facts=tuple(
                CandidateFact.from_dict(f) for f in data.get("candidate_facts", [])
            ),
            succeeded=bool(data["succeeded"]),
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def success(
        cls,
        document_id: DocumentId,
        source_id: SourceId,
        extractor_id: ExtractorId,
        candidate_facts: tuple[CandidateFact, ...],
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        return cls(
            extraction_result_id=generate_extraction_result_id(),
            document_id=document_id,
            source_id=source_id,
            extractor_id=extractor_id,
            candidate_facts=candidate_facts,
            succeeded=True,
            extracted_at=utcnow(),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def failure(
        cls,
        document_id: DocumentId,
        source_id: SourceId,
        extractor_id: ExtractorId,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        return cls(
            extraction_result_id=generate_extraction_result_id(),
            document_id=document_id,
            source_id=source_id,
            extractor_id=extractor_id,
            candidate_facts=(),
            succeeded=False,
            extracted_at=utcnow(),
            metadata=dict(metadata) if metadata is not None else {},
        )
