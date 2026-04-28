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

    def system_summary(self) -> dict:
        try:
            from db.database import Database

            with Database() as db:
                rows = db.fetchall(
                    "SELECT completeness, freshness, consistency FROM knowledge_objects "
                    "WHERE state = ?",
                    ("ACTIVE",),
                )

            if not rows:
                return {
                    "trust_score": None,
                    "completeness": None,
                    "freshness": None,
                    "consistency": None,
                }

            avg = lambda key: round(sum(r[key] for r in rows) / len(rows) * 100)

            completeness = avg("completeness")
            freshness = avg("freshness")
            consistency = avg("consistency")
            trust_score = round((completeness + freshness + consistency) / 3)

            return {
                "trust_score": trust_score,
                "completeness": completeness,
                "freshness": freshness,
                "consistency": consistency,
            }

        except Exception:
            return {
                "trust_score": None,
                "completeness": None,
                "freshness": None,
                "consistency": None,
            }

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
