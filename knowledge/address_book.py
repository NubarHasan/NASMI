from dataclasses import dataclass, field
from enum import Enum
from core.events import Event, EventType
from core.event_bus import bus


class FieldStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class FieldEntry:
    value: str
    tag: str
    priority: int = 1
    status: FieldStatus = FieldStatus.ACTIVE
    source: str = ""
    confidence: float = 1.0

    def archive(self) -> None:
        self.status = FieldStatus.ARCHIVED

    def is_active(self) -> bool:
        return self.status == FieldStatus.ACTIVE

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "tag": self.tag,
            "priority": self.priority,
            "status": self.status.value,
            "source": self.source,
            "confidence": self.confidence,
        }


class FieldBook:

    def __init__(self):
        self._store: dict[str, list[FieldEntry]] = {}

    def add(self, field_type: str, entry: FieldEntry) -> None:
        self._store.setdefault(field_type, [])

        if self._is_duplicate(field_type, entry):
            return

        self._store[field_type].append(entry)

        bus.publish(
            Event(
                event_type=EventType.ENTITY_MERGED,
                payload={
                    "field_type": field_type,
                    "tag": entry.tag,
                    "value": entry.value,
                },
                source="field_book",
            )
        )

    def get(self, field_type: str, tag: str | None = None) -> list[FieldEntry]:
        entries = self._store.get(field_type, [])
        active = [e for e in entries if e.is_active()]

        if tag:
            active = [e for e in active if e.tag == tag]

        return sorted(active, key=lambda e: e.priority, reverse=True)

    def top(self, field_type: str, tag: str | None = None) -> FieldEntry | None:
        entries = self.get(field_type, tag)
        return entries[0] if entries else None

    def archive(self, field_type: str, tag: str) -> None:
        for entry in self._store.get(field_type, []):
            if entry.tag == tag and entry.is_active():
                entry.archive()

    def all_dicts(self, field_type: str) -> list[dict]:
        return [e.to_dict() for e in self._store.get(field_type, [])]

    def _is_duplicate(self, field_type: str, entry: FieldEntry) -> bool:
        return any(
            e.value == entry.value and e.tag == entry.tag and e.is_active()
            for e in self._store.get(field_type, [])
        )
