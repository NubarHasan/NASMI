from dataclasses import dataclass, field
from datetime import datetime, timezone
from knowledge.knowledge_objects import KnowledgeObject
from core.events import Event, EventType
from core.event_bus import bus


@dataclass
class VersionRecord:
    version: int
    obj: KnowledgeObject
    changed_by: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "changed_by": self.changed_by,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "object": self.obj.to_dict(),
        }


class Versioning:

    def __init__(self):
        self._history: dict[str, list[VersionRecord]] = {}

    def record(
        self, obj: KnowledgeObject, changed_by: str = "system", reason: str = ""
    ) -> int:
        key = obj.id
        records = self._history.setdefault(key, [])
        version = len(records) + 1

        records.append(
            VersionRecord(
                version=version,
                obj=obj,
                changed_by=changed_by,
                reason=reason,
            )
        )

        bus.publish(
            Event(
                event_type=EventType.ENTITY_VALIDATED,
                payload={"id": key, "version": version, "reason": reason},
                source="versioning",
            )
        )

        return version

    def history(self, obj_id: str) -> list[VersionRecord]:
        return self._history.get(obj_id, [])

    def latest(self, obj_id: str) -> VersionRecord | None:
        records = self._history.get(obj_id, [])
        return records[-1] if records else None

    def rollback(self, obj_id: str, version: int) -> KnowledgeObject | None:
        records = self._history.get(obj_id, [])
        for r in records:
            if r.version == version:
                return r.obj
        return None

    def to_dict(self, obj_id: str) -> list[dict]:
        return [r.to_dict() for r in self.history(obj_id)]


versioning = Versioning()
