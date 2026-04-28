import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class KnowledgeState(Enum):
    NEW = "new"
    VALIDATED = "validated"
    ACTIVE = "active"
    ARCHIVED = "archived"
    CONFLICTED = "conflicted"
    EXPIRED = "expired"


class FieldType(Enum):
    IDENTITY = "identity"
    ADDRESS = "address"
    CONTACT = "contact"
    FINANCIAL = "financial"
    LEGAL = "legal"
    EMPLOYMENT = "employment"
    DOCUMENT = "document"
    OTHER = "other"


@dataclass
class Confidence:
    ocr: float = 0.0
    ner: float = 0.0
    context: float = 0.0

    @property
    def final(self) -> float:
        weights = [0.2, 0.5, 0.3]
        return round(
            sum(v * w for v, w in zip([self.ocr, self.ner, self.context], weights)), 2
        )

    def to_dict(self) -> dict:
        return {
            "ocr": self.ocr,
            "ner": self.ner,
            "context": self.context,
            "final": self.final,
        }


@dataclass
class Provenance:
    document_id: str = ""
    page: int = 0
    bbox: tuple = field(default_factory=tuple)
    method: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "page": self.page,
            "bbox": self.bbox,
            "method": self.method,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Quality:
    completeness: float = 0.0
    freshness: float = 0.0
    consistency: float = 0.0

    @property
    def trust_score(self) -> float:
        weights = [0.4, 0.3, 0.3]
        return round(
            sum(
                v * w
                for v, w in zip(
                    [self.completeness, self.freshness, self.consistency], weights
                )
            ),
            2,
        )

    def to_dict(self) -> dict:
        return {
            "completeness": self.completeness,
            "freshness": self.freshness,
            "consistency": self.consistency,
            "trust_score": self.trust_score,
        }


@dataclass
class KnowledgeObject:
    value: str
    field_type: FieldType = FieldType.OTHER
    state: KnowledgeState = KnowledgeState.NEW
    confidence: Confidence = field(default_factory=Confidence)
    provenance: Provenance = field(default_factory=Provenance)
    quality: Quality = field(default_factory=Quality)
    tags: list = field(default_factory=list)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def is_trusted(self, threshold: float = 0.85) -> bool:
        return self.confidence.final >= threshold

    def is_active(self) -> bool:
        return self.state == KnowledgeState.ACTIVE

    def is_expired(self) -> bool:
        if self.valid_to is None:
            return False
        return datetime.now(timezone.utc) > self.valid_to

    def archive(self) -> None:
        self.state = KnowledgeState.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)

    def expire(self) -> None:
        self.state = KnowledgeState.EXPIRED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "value": self.value,
            "field_type": self.field_type.value,
            "state": self.state.value,
            "confidence": self.confidence.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "tags": self.tags,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
