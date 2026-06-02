from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_extraction_result_id,
    is_valid_extraction_result_id,
    is_valid_source_id,
)
from core.types import (
    ExtractionResultId,
    SourceId,
)
from processing.extraction.candidate_fact import CandidateFact


@dataclass(frozen=True)
class ExtractionResult:
    extraction_result_id: ExtractionResultId
    source_id: SourceId
    candidate_facts: tuple[CandidateFact, ...]
    succeeded: bool
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_extraction_result_id(self.extraction_result_id),
            f"Invalid ExtractionResultId: [{self.extraction_result_id}]",
        )
        require(
            is_valid_source_id(self.source_id),
            f"Invalid SourceId: [{self.source_id}]",
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
            isinstance(self.succeeded, bool),
            "succeeded must be a bool",
        )
        require(
            isinstance(self.created_at, datetime),
            "created_at must be a datetime instance",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )
        require(
            self.succeeded or len(self.candidate_facts) == 0,
            "failed ExtractionResult must not contain candidate_facts",
        )
        require(
            all(f.source_id == self.source_id for f in self.candidate_facts),
            "all candidate_facts must share the same source_id as ExtractionResult",
        )

    @property
    def candidate_count(self) -> int:
        return len(self.candidate_facts)

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

    @property
    def is_empty(self) -> bool:
        return len(self.candidate_facts) == 0

    def with_metadata(self, key: str, value: Any) -> ExtractionResult:
        return ExtractionResult(
            **{**self.__dict__, "metadata": {**self.metadata, key: value}},
        )

    @classmethod
    def success(
        cls,
        source_id: SourceId,
        candidate_facts: tuple[CandidateFact, ...],
        created_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        require(
            len(candidate_facts) > 0,
            "successful ExtractionResult must contain at least one CandidateFact",
        )
        return cls(
            extraction_result_id=generate_extraction_result_id(),
            source_id=source_id,
            candidate_facts=candidate_facts,
            succeeded=True,
            created_at=created_at,
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def failure(
        cls,
        source_id: SourceId,
        created_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        return cls(
            extraction_result_id=generate_extraction_result_id(),
            source_id=source_id,
            candidate_facts=(),
            succeeded=False,
            created_at=created_at,
            metadata=dict(metadata) if metadata is not None else {},
        )
