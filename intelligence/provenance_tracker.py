from dataclasses import dataclass, field
from datetime import datetime
from core.event_bus import bus
from core.events import Event, EventType


@dataclass
class ProvenanceRecord:
    file_hash: str
    filename: str
    source: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file_hash": self.file_hash,
            "filename": self.filename,
            "source": self.source,
            "action": self.action,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class ProvenanceTracker:

    def __init__(self) -> None:
        self._records: list[ProvenanceRecord] = []
        bus.subscribe(EventType.ENTITIES_EXTRACTED, self._on_extracted)

    def record(
        self,
        file_hash: str,
        filename: str,
        source: str,
        action: str,
        details: dict | None = None,
    ) -> None:
        entry = ProvenanceRecord(
            file_hash=file_hash,
            filename=filename,
            source=source,
            action=action,
            details=details or {},
        )
        self._records.append(entry)
        bus.publish(
            Event(
                event_type=EventType.PROVENANCE_RECORDED,
                payload=entry.to_dict(),
                source="provenance_tracker",
            )
        )

    def get_history(self, file_hash: str) -> list[dict]:
        return [r.to_dict() for r in self._records if r.file_hash == file_hash]

    def get_all(self) -> list[dict]:
        return [r.to_dict() for r in self._records]

    def _on_extracted(self, event: Event) -> None:
        self.record(
            file_hash=event.payload.get("file_hash", ""),
            filename=event.payload.get("filename", ""),
            source=event.source,
            action="entities_extracted",
            details={
                "confidence": event.payload.get("entities", {}).get("confidence", 0)
            },
        )
