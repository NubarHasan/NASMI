from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class EventType(Enum):
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_EXPIRED = "document.expired"
    ENTITIES_EXTRACTED = "entities.extracted"
    QUALITY_SCORED = "quality.scored"
    ENTITY_VALIDATED = "entity.validated"
    ENTITY_MERGED = "entity.merged"
    IDENTITY_UPDATED = "identity.updated"
    PREDICTION_GENERATED = "prediction.generated"
    CONFLICT_DETECTED = "conflict.detected"
    REVIEW_REQUIRED = "review.required"
    EXPORT_GENERATED = "export.generated"
    FORM_FILLED = "form.filled"
    PROVENANCE_RECORDED = "provenance.recorded"


@dataclass
class Event:
    event_type: EventType
    payload: dict = field(default_factory=dict)
    source: str = "system"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            import uuid

            self.event_id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }
