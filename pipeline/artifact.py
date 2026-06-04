from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from core.exceptions import ValidationError
from core.guards import require
from core.identifiers import generate_artifact_id
from core.time import format_timestamp, parse_timestamp, utcnow
from output.output_format import OutputFormat
from output.output_type import OutputType


class ArtifactType(StrEnum):
    DOCUMENT = "document"
    EVIDENCE = "evidence"
    EXTRACTION = "extraction"
    ENTITY_RESOLUTION = "entity_resolution"
    KNOWLEDGE_BUILD = "knowledge_build"
    FACT_ACCEPTANCE = "fact_acceptance"
    FACT = "fact"
    OCR = "ocr"
    PROFILE = "profile"
    OUTPUT = "output"
    INTERMEDIATE = "intermediate"


def _validate_source_ids(source_artifact_ids: tuple[str, ...]) -> None:
    require(
        all(isinstance(x, str) and x for x in source_artifact_ids),
        "source_artifact_ids must contain non-empty strings",
    )


@dataclass(frozen=True)
class BaseArtifact:
    artifact_id: str
    artifact_type: ArtifactType
    job_id: str
    stage: str
    created_at: datetime
    source_artifact_ids: tuple[str, ...]

    def is_root(self) -> bool:
        return not self.source_artifact_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": str(self.artifact_type),
            "job_id": self.job_id,
            "stage": self.stage,
            "created_at": format_timestamp(self.created_at),
            "source_artifact_ids": list(self.source_artifact_ids),
        }

    @staticmethod
    def _base_fields(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifact_id": data["artifact_id"],
            "artifact_type": ArtifactType(data["artifact_type"]),
            "job_id": data["job_id"],
            "stage": data["stage"],
            "created_at": parse_timestamp(data["created_at"]),
            "source_artifact_ids": tuple(data.get("source_artifact_ids", [])),
        }


@dataclass(frozen=True)
class DocumentArtifact(BaseArtifact):
    document_id: str
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["document_id"] = self.document_id
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            document_id=data["document_id"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        document_id: str,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> DocumentArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(document_id), "document_id must be non-empty")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.DOCUMENT,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            document_id=document_id,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class EvidenceArtifact(BaseArtifact):
    evidence_id: str
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["evidence_id"] = self.evidence_id
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            evidence_id=data["evidence_id"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        evidence_id: str,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> EvidenceArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(evidence_id), "evidence_id must be non-empty")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.EVIDENCE,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            evidence_id=evidence_id,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class ExtractionArtifact(BaseArtifact):
    document_id: str
    source_id: str
    extractor_id: str
    candidate_fact_count: int
    mean_confidence: float
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["document_id"] = self.document_id
        base["source_id"] = self.source_id
        base["extractor_id"] = self.extractor_id
        base["candidate_fact_count"] = self.candidate_fact_count
        base["mean_confidence"] = self.mean_confidence
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            document_id=data["document_id"],
            source_id=data["source_id"],
            extractor_id=data["extractor_id"],
            candidate_fact_count=data["candidate_fact_count"],
            mean_confidence=data["mean_confidence"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        document_id: str,
        source_id: str,
        extractor_id: str,
        candidate_fact_count: int,
        mean_confidence: float,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> ExtractionArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(document_id), "document_id must be non-empty")
        require(bool(source_id), "source_id must be non-empty")
        require(bool(extractor_id), "extractor_id must be non-empty")
        require(
            isinstance(candidate_fact_count, int) and candidate_fact_count >= 0,
            "candidate_fact_count must be a non-negative int",
        )
        require(
            0.0 <= mean_confidence <= 1.0,
            "mean_confidence must be in [0.0, 1.0]",
        )
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.EXTRACTION,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            document_id=document_id,
            source_id=source_id,
            extractor_id=extractor_id,
            candidate_fact_count=candidate_fact_count,
            mean_confidence=mean_confidence,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class EntityResolutionArtifact(BaseArtifact):
    entity_id: str
    fact_count: int
    resolution_confidence: float
    has_conflicts: bool
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["entity_id"] = self.entity_id
        base["fact_count"] = self.fact_count
        base["resolution_confidence"] = self.resolution_confidence
        base["has_conflicts"] = self.has_conflicts
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityResolutionArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            entity_id=data["entity_id"],
            fact_count=data["fact_count"],
            resolution_confidence=data["resolution_confidence"],
            has_conflicts=data["has_conflicts"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        entity_id: str,
        fact_count: int,
        resolution_confidence: float,
        has_conflicts: bool,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> EntityResolutionArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(entity_id), "entity_id must be non-empty")
        require(
            isinstance(fact_count, int) and fact_count > 0,
            "fact_count must be a positive int",
        )
        require(
            0.0 <= resolution_confidence <= 1.0,
            "resolution_confidence must be in [0.0, 1.0]",
        )
        require(isinstance(has_conflicts, bool), "has_conflicts must be a bool")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.ENTITY_RESOLUTION,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            entity_id=entity_id,
            fact_count=fact_count,
            resolution_confidence=resolution_confidence,
            has_conflicts=has_conflicts,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class KnowledgeBuildArtifact(BaseArtifact):
    entity_id: str
    fact_count: int
    evidence_count: int
    conflict_count: int
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["entity_id"] = self.entity_id
        base["fact_count"] = self.fact_count
        base["evidence_count"] = self.evidence_count
        base["conflict_count"] = self.conflict_count
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeBuildArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            entity_id=data["entity_id"],
            fact_count=data["fact_count"],
            evidence_count=data["evidence_count"],
            conflict_count=data["conflict_count"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        entity_id: str,
        fact_count: int,
        evidence_count: int,
        conflict_count: int,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> KnowledgeBuildArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(entity_id), "entity_id must be non-empty")
        require(
            isinstance(fact_count, int) and fact_count >= 0,
            "fact_count must be a non-negative int",
        )
        require(
            isinstance(evidence_count, int) and evidence_count >= 0,
            "evidence_count must be a non-negative int",
        )
        require(
            isinstance(conflict_count, int) and conflict_count >= 0,
            "conflict_count must be a non-negative int",
        )
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.KNOWLEDGE_BUILD,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            entity_id=entity_id,
            fact_count=fact_count,
            evidence_count=evidence_count,
            conflict_count=conflict_count,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class FactAcceptanceArtifact(BaseArtifact):
    entity_id: str
    accepted_count: int
    review_required_count: int
    conflict_count: int
    rejected_count: int
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["entity_id"] = self.entity_id
        base["accepted_count"] = self.accepted_count
        base["review_required_count"] = self.review_required_count
        base["conflict_count"] = self.conflict_count
        base["rejected_count"] = self.rejected_count
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactAcceptanceArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            entity_id=data["entity_id"],
            accepted_count=data["accepted_count"],
            review_required_count=data["review_required_count"],
            conflict_count=data["conflict_count"],
            rejected_count=data["rejected_count"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        entity_id: str,
        accepted_count: int,
        review_required_count: int,
        conflict_count: int,
        rejected_count: int,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> FactAcceptanceArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(entity_id), "entity_id must be non-empty")
        require(
            isinstance(accepted_count, int) and accepted_count >= 0,
            "accepted_count must be a non-negative int",
        )
        require(
            isinstance(review_required_count, int) and review_required_count >= 0,
            "review_required_count must be a non-negative int",
        )
        require(
            isinstance(conflict_count, int) and conflict_count >= 0,
            "conflict_count must be a non-negative int",
        )
        require(
            isinstance(rejected_count, int) and rejected_count >= 0,
            "rejected_count must be a non-negative int",
        )
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.FACT_ACCEPTANCE,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            entity_id=entity_id,
            accepted_count=accepted_count,
            review_required_count=review_required_count,
            conflict_count=conflict_count,
            rejected_count=rejected_count,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class FactArtifact(BaseArtifact):
    fact_id: str
    entity_id: str
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["fact_id"] = self.fact_id
        base["entity_id"] = self.entity_id
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            fact_id=data["fact_id"],
            entity_id=data["entity_id"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        fact_id: str,
        entity_id: str,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> FactArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(fact_id), "fact_id must be non-empty")
        require(bool(entity_id), "entity_id must be non-empty")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.FACT,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            fact_id=fact_id,
            entity_id=entity_id,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class OcrArtifact(BaseArtifact):
    document_id: str
    source_id: str
    page_count: int
    mean_confidence: float
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["document_id"] = self.document_id
        base["source_id"] = self.source_id
        base["page_count"] = self.page_count
        base["mean_confidence"] = self.mean_confidence
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OcrArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            document_id=data["document_id"],
            source_id=data["source_id"],
            page_count=data["page_count"],
            mean_confidence=data["mean_confidence"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        document_id: str,
        source_id: str,
        page_count: int,
        mean_confidence: float,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> OcrArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(document_id), "document_id must be non-empty")
        require(bool(source_id), "source_id must be non-empty")
        require(
            isinstance(page_count, int) and page_count >= 0,
            "page_count must be a non-negative int",
        )
        require(
            0.0 <= mean_confidence <= 1.0,
            "mean_confidence must be in [0.0, 1.0]",
        )
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.OCR,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            document_id=document_id,
            source_id=source_id,
            page_count=page_count,
            mean_confidence=mean_confidence,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class ProfileArtifact(BaseArtifact):
    entity_id: str
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["entity_id"] = self.entity_id
        base["snapshot"] = copy.deepcopy(self.snapshot)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            entity_id=data["entity_id"],
            snapshot=copy.deepcopy(data["snapshot"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        entity_id: str,
        snapshot: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> ProfileArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(entity_id), "entity_id must be non-empty")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.PROFILE,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            entity_id=entity_id,
            snapshot=copy.deepcopy(snapshot),
        )


@dataclass(frozen=True)
class OutputArtifact(BaseArtifact):
    entity_id: str
    output_document_id: str
    output_type: OutputType
    output_format: OutputFormat
    file_path: str

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["entity_id"] = self.entity_id
        base["output_document_id"] = self.output_document_id
        base["output_type"] = str(self.output_type)
        base["output_format"] = str(self.output_format)
        base["file_path"] = self.file_path
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutputArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            entity_id=data["entity_id"],
            output_document_id=data["output_document_id"],
            output_type=OutputType(data["output_type"]),
            output_format=OutputFormat(data["output_format"]),
            file_path=data["file_path"],
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        entity_id: str,
        output_document_id: str,
        output_type: OutputType,
        output_format: OutputFormat,
        file_path: str,
        source_artifact_ids: tuple[str, ...] = (),
    ) -> OutputArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(entity_id), "entity_id must be non-empty")
        require(bool(output_document_id), "output_document_id must be non-empty")
        require(
            isinstance(output_type, OutputType), "output_type must be an OutputType"
        )
        require(
            isinstance(output_format, OutputFormat),
            "output_format must be an OutputFormat",
        )
        require(bool(file_path), "file_path must be non-empty")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.OUTPUT,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            entity_id=entity_id,
            output_document_id=output_document_id,
            output_type=output_type,
            output_format=output_format,
            file_path=file_path,
        )


@dataclass(frozen=True)
class IntermediateArtifact(BaseArtifact):
    key: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["key"] = self.key
        base["payload"] = copy.deepcopy(self.payload)
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntermediateArtifact:
        return cls(
            **BaseArtifact._base_fields(data),
            key=data["key"],
            payload=copy.deepcopy(data["payload"]),
        )

    @classmethod
    def create(
        cls,
        job_id: str,
        stage: str,
        key: str,
        payload: dict[str, Any],
        source_artifact_ids: tuple[str, ...] = (),
    ) -> IntermediateArtifact:
        require(bool(job_id), "job_id must be non-empty")
        require(bool(stage), "stage must be non-empty")
        require(bool(key), "key must be non-empty")
        _validate_source_ids(source_artifact_ids)
        return cls(
            artifact_id=generate_artifact_id(),
            artifact_type=ArtifactType.INTERMEDIATE,
            job_id=job_id,
            stage=stage,
            created_at=utcnow(),
            source_artifact_ids=source_artifact_ids,
            key=key,
            payload=copy.deepcopy(payload),
        )


Artifact = (
    DocumentArtifact
    | EvidenceArtifact
    | ExtractionArtifact
    | EntityResolutionArtifact
    | KnowledgeBuildArtifact
    | FactAcceptanceArtifact
    | FactArtifact
    | OcrArtifact
    | ProfileArtifact
    | OutputArtifact
    | IntermediateArtifact
)


class _ArtifactDecoder(Protocol):
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Artifact: ...


_ARTIFACT_REGISTRY: dict[str, _ArtifactDecoder] = {
    ArtifactType.DOCUMENT: DocumentArtifact,
    ArtifactType.EVIDENCE: EvidenceArtifact,
    ArtifactType.EXTRACTION: ExtractionArtifact,
    ArtifactType.ENTITY_RESOLUTION: EntityResolutionArtifact,
    ArtifactType.KNOWLEDGE_BUILD: KnowledgeBuildArtifact,
    ArtifactType.FACT_ACCEPTANCE: FactAcceptanceArtifact,
    ArtifactType.FACT: FactArtifact,
    ArtifactType.OCR: OcrArtifact,
    ArtifactType.PROFILE: ProfileArtifact,
    ArtifactType.OUTPUT: OutputArtifact,
    ArtifactType.INTERMEDIATE: IntermediateArtifact,
}


def artifact_from_dict(data: dict[str, Any]) -> Artifact:
    artifact_type = data.get("artifact_type", "")
    decoder = _ARTIFACT_REGISTRY.get(artifact_type)
    if decoder is None:
        raise ValidationError(f"Unknown artifact_type: {artifact_type!r}")
    return decoder.from_dict(data)


@dataclass
class ArtifactBundle:
    job_id: str

    _order: list[Artifact] = field(default_factory=list, repr=False, init=False)
    _by_id: dict[str, Artifact] = field(default_factory=dict, repr=False, init=False)
    _by_type: dict[ArtifactType, list[Artifact]] = field(
        default_factory=dict, repr=False, init=False
    )
    _by_stage: dict[str, list[Artifact]] = field(
        default_factory=dict, repr=False, init=False
    )
    _frozen: bool = field(default=False, repr=False, init=False)

    def add(self, artifact: Artifact) -> None:
        require(not self._frozen, "ArtifactBundle is frozen — job is complete")
        require(
            artifact.job_id == self.job_id,
            f"artifact.job_id {artifact.job_id!r} != bundle.job_id {self.job_id!r}",
        )
        require(
            artifact.artifact_id not in self._by_id,
            f"duplicate artifact_id: {artifact.artifact_id!r}",
        )
        self._order.append(artifact)
        self._by_id[artifact.artifact_id] = artifact
        self._by_type.setdefault(artifact.artifact_type, []).append(artifact)
        self._by_stage.setdefault(artifact.stage, []).append(artifact)

    def freeze(self) -> None:
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def get(self, artifact_id: str) -> Artifact | None:
        return self._by_id.get(artifact_id)

    def by_type(self, artifact_type: ArtifactType) -> list[Artifact]:
        return list(self._by_type.get(artifact_type, []))

    def by_stage(self, stage: str) -> list[Artifact]:
        return list(self._by_stage.get(stage, []))

    def all(self) -> list[Artifact]:
        return list(self._order)

    def summary(self) -> dict[str, int]:
        return {str(t): len(self._by_type.get(t, [])) for t in ArtifactType}

    def __len__(self) -> int:
        return len(self._order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "is_frozen": self._frozen,
            "items": [a.to_dict() for a in self._order],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactBundle:
        bundle = cls(job_id=data["job_id"])
        for item in data.get("items", []):
            bundle.add(artifact_from_dict(item))
        if data.get("is_frozen", False):
            bundle.freeze()
        return bundle
