from dataclasses import dataclass, field
from datetime import datetime
from knowledge.knowledge_objects import KnowledgeObject, FieldType
from core.events import Event, EventType
from core.event_bus import bus


LIFE_EVENT_RULES: dict[str, set[FieldType]] = {
    "relocation": {FieldType.ADDRESS},
    "employment": {FieldType.EMPLOYMENT, FieldType.FINANCIAL},
    "identification": {FieldType.IDENTITY, FieldType.DOCUMENT},
    "legal": {FieldType.LEGAL, FieldType.IDENTITY},
    "financial": {FieldType.FINANCIAL, FieldType.DOCUMENT},
    "contact_update": {FieldType.CONTACT},
}


@dataclass
class LifeEvent:
    cluster_id: str
    label: str
    objects: list[KnowledgeObject] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def add(self, obj: KnowledgeObject) -> None:
        self.objects.append(obj)

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "object_count": len(self.objects),
            "detected_at": self.detected_at.isoformat(),
            "values": [o.value for o in self.objects],
        }


class LifeEventCluster:

    def __init__(self):
        self._clusters: dict[str, LifeEvent] = {}

    def cluster(self, objects: list[KnowledgeObject]) -> list[LifeEvent]:
        self._clusters.clear()

        for obj in objects:
            label = self._match_label(obj.field_type)
            if not label:
                continue

            if label not in self._clusters:
                self._clusters[label] = LifeEvent(
                    cluster_id=label,
                    label=label,
                )

            self._clusters[label].add(obj)

        for cluster in self._clusters.values():
            bus.publish(
                Event(
                    event_type=EventType.PREDICTION_GENERATED,
                    payload=cluster.to_dict(),
                    source="life_event_cluster",
                )
            )

        return list(self._clusters.values())

    def get(self, label: str) -> LifeEvent | None:
        return self._clusters.get(label)

    def all_dicts(self) -> list[dict]:
        return [c.to_dict() for c in self._clusters.values()]

    def _match_label(self, field_type: FieldType) -> str | None:
        for label, types in LIFE_EVENT_RULES.items():
            if field_type in types:
                return label
        return None
