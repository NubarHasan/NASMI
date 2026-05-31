from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from core.exceptions import ValidationError
from core.guards import require
from core.identifiers import generate_artifact_id
from core.time import utcnow_iso


class ArtifactType(StrEnum):
    DOCUMENT = "document"
    EVIDENCE = "evidence"
    FACT = "fact"
    PROFILE = "profile"
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
    created_at: str
    source_artifact_ids: tuple[str, ...]

    def is_root(self) -> bool:
        return not self.source_artifact_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": str(self.artifact_type),
            "job_id": self.job_id,
            "stage": self.stage,
            "created_at": self.created_at,
            "source_artifact_ids": list(self.source_artifact_ids),
        }

    @staticmethod
    def _base_fields(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifact_id": data["artifact_id"],
            "artifact_type": ArtifactType(data["artifact_type"]),
            "job_id": data["job_id"],
            "stage": data["stage"],
            "created_at": data["created_at"],
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
            created_at=utcnow_iso(),
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
            created_at=utcnow_iso(),
            source_artifact_ids=source_artifact_ids,
            evidence_id=evidence_id,
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
            created_at=utcnow_iso(),
            source_artifact_ids=source_artifact_ids,
            fact_id=fact_id,
            entity_id=entity_id,
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
            created_at=utcnow_iso(),
            source_artifact_ids=source_artifact_ids,
            entity_id=entity_id,
            snapshot=copy.deepcopy(snapshot),
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
            created_at=utcnow_iso(),
            source_artifact_ids=source_artifact_ids,
            key=key,
            payload=copy.deepcopy(payload),
        )


Artifact = (
    DocumentArtifact
    | EvidenceArtifact
    | FactArtifact
    | ProfileArtifact
    | IntermediateArtifact
)


class _ArtifactDecoder(Protocol):
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Artifact: ...


_ARTIFACT_REGISTRY: dict[str, _ArtifactDecoder] = {
    ArtifactType.DOCUMENT: DocumentArtifact,
    ArtifactType.EVIDENCE: EvidenceArtifact,
    ArtifactType.FACT: FactArtifact,
    ArtifactType.PROFILE: ProfileArtifact,
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
