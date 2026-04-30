from dataclasses import dataclass, field
from datetime import datetime, timezone
from knowledge.knowledge_objects import KnowledgeObject, FieldType
from knowledge.risk_engine import RiskEngine, RiskResult
from core.events import Event, EventType
from core.event_bus import bus


FROZEN_FIELDS = {
    FieldType.IDENTITY,
}


@dataclass
class Contradiction:
    field_type:   str
    existing:     str
    incoming:     str
    reason:       str
    severity:     str
    risk:         RiskResult
    detected_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            'field_type':  self.field_type,
            'existing':    self.existing,
            'incoming':    self.incoming,
            'reason':      self.reason,
            'severity':    self.severity,
            'risk_score':  self.risk.risk_score,
            'detected_at': self.detected_at.isoformat(),
        }


class ContradictionEngine:

    def __init__(self):
        self._risk_engine = RiskEngine()

    def check(
        self,
        existing: KnowledgeObject,
        incoming: KnowledgeObject,
    ) -> Contradiction | None:

        if existing.field_type != incoming.field_type:
            return None

        if existing.value == incoming.value:
            return None

        if self._is_temporal_shift(existing, incoming):
            return None

        if self._is_tag_difference(existing, incoming):
            return None

        severity = self._severity(existing, incoming)
        reason   = self._reason(existing, incoming)
        risk     = self._risk_engine.evaluate(incoming)

        contradiction = Contradiction(
            field_type = existing.field_type.value,
            existing   = existing.value,
            incoming   = incoming.value,
            reason     = reason,
            severity   = severity,
            risk       = risk,
        )

        bus.publish(Event(
            event_type = EventType.CONFLICT_DETECTED,
            payload    = contradiction.to_dict(),
            source     = 'contradiction_engine',
        ))

        return contradiction

    def check_batch(
        self,
        existing_objects: list[KnowledgeObject],
        incoming:         KnowledgeObject,
    ) -> list[Contradiction]:

        results = []
        for existing in existing_objects:
            result = self.check(existing, incoming)
            if result:
                results.append(result)
        return results

    def _is_temporal_shift(
        self,
        existing: KnowledgeObject,
        incoming: KnowledgeObject,
    ) -> bool:
        if existing.valid_to and incoming.valid_from:
            return incoming.valid_from >= existing.valid_to
        return False

    def _is_tag_difference(
        self,
        existing: KnowledgeObject,
        incoming: KnowledgeObject,
    ) -> bool:
        if not existing.tags or not incoming.tags:
            return False
        return not bool(set(existing.tags) & set(incoming.tags))

    def _severity(
        self,
        existing: KnowledgeObject,
        incoming: KnowledgeObject,
    ) -> str:
        if existing.field_type in FROZEN_FIELDS:
            return 'critical'
        if incoming.confidence.final < 0.5:
            return 'suspicious'
        return 'low'

    def _reason(
        self,
        existing: KnowledgeObject,
        incoming: KnowledgeObject,
    ) -> str:
        if existing.field_type in FROZEN_FIELDS:
            return f'frozen field conflict: {existing.field_type.value}'
        if existing.tags and incoming.tags and existing.tags == incoming.tags:
            return 'same field + same tag + overlapping time'
        return 'value mismatch with no temporal or tag justification'
