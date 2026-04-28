from datetime import datetime, timezone
from knowledge.knowledge_objects import KnowledgeObject, KnowledgeState, Quality
from core.events import Event, EventType
from core.event_bus import bus


class QualityEngine:

    FRESHNESS_DECAY_DAYS = 365

    def score(self, obj: KnowledgeObject) -> KnowledgeObject:
        obj.quality = Quality(
            completeness=self._completeness(obj),
            freshness=self._freshness(obj),
            consistency=self._consistency(obj),
        )

        bus.publish(
            Event(
                event_type=EventType.QUALITY_SCORED,
                payload={
                    "value": obj.value,
                    "field_type": obj.field_type.value,
                    "trust_score": obj.quality.trust_score,
                },
                source="quality_engine",
            )
        )

        return obj

    def score_batch(self, objects: list[KnowledgeObject]) -> list[KnowledgeObject]:
        return [self.score(obj) for obj in objects]

    def _completeness(self, obj: KnowledgeObject) -> float:
        filled = [
            bool(obj.value),
            obj.field_type is not None,
            bool(obj.tags),
            obj.provenance.document_id != "",
            obj.valid_from is not None,
        ]
        return round(sum(filled) / len(filled), 2)

    def _freshness(self, obj: KnowledgeObject) -> float:
        if obj.valid_from is None:
            return 0.0

        now = datetime.now(timezone.utc)
        ref = obj.valid_to if obj.valid_to else obj.valid_from
        diff = (now - ref).days

        if diff <= 0:
            return 1.0

        score = 1.0 - (diff / self.FRESHNESS_DECAY_DAYS)
        return round(max(0.0, score), 2)

    def _consistency(self, obj: KnowledgeObject) -> float:
        if obj.state == KnowledgeState.CONFLICTED:
            return 0.0
        if obj.state == KnowledgeState.EXPIRED:
            return 0.3
        if obj.state == KnowledgeState.ARCHIVED:
            return 0.6
        if obj.state in (KnowledgeState.ACTIVE, KnowledgeState.VALIDATED):
            return 1.0
        return 0.8
