from dataclasses import dataclass, field
from datetime import datetime, timezone
from knowledge.knowledge_objects import KnowledgeObject, KnowledgeState
from core.events import Event, EventType
from core.event_bus import bus


@dataclass
class FieldEntry:
    obj: KnowledgeObject
    tag: str
    priority: int = 0

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "priority": self.priority,
            "object": self.obj.to_dict(),
        }


class FieldBook:

    def __init__(self):
        self._store: dict[str, list[FieldEntry]] = {}

    def add(
        self,
        field_name: str,
        obj: KnowledgeObject,
        tag: str = "default",
        priority: int = 0,
    ) -> None:
        if field_name not in self._store:
            self._store[field_name] = []

        self._store[field_name].append(FieldEntry(obj=obj, tag=tag, priority=priority))
        self._store[field_name].sort(key=lambda e: e.priority, reverse=True)

        bus.publish(
            Event(
                event_type=EventType.ENTITY_MERGED,
                payload={"field": field_name, "tag": tag, "value": obj.value},
                source="field_book",
            )
        )

    def get(self, field_name: str, tag: str | None = None) -> list[FieldEntry]:
        entries = self._store.get(field_name, [])
        if tag:
            return [e for e in entries if e.tag == tag]
        return entries

    def get_top(self, field_name: str, tag: str | None = None) -> FieldEntry | None:
        entries = self.get(field_name, tag)
        return entries[0] if entries else None

    def all_fields(self) -> list[str]:
        return list(self._store.keys())

    def archive(self, field_name: str, tag: str) -> None:
        for entry in self._store.get(field_name, []):
            if entry.tag == tag:
                entry.obj.archive()

    def to_dict(self) -> dict:
        return {
            field_name: [e.to_dict() for e in entries]
            for field_name, entries in self._store.items()
        }
