from dataclasses import dataclass
from knowledge.knowledge_objects import KnowledgeObject, KnowledgeState, FieldType
from core.events import Event, EventType
from core.event_bus import bus


FIELD_SENSITIVITY = {
    FieldType.IDENTITY: 1.0,
    FieldType.FINANCIAL: 0.9,
    FieldType.LEGAL: 0.8,
    FieldType.EMPLOYMENT: 0.6,
    FieldType.ADDRESS: 0.5,
    FieldType.CONTACT: 0.4,
    FieldType.DOCUMENT: 0.3,
    FieldType.OTHER: 0.2,
}


@dataclass
class RiskResult:
    object_value: str
    field_type: str
    risk_score: float
    level: str
    reasons: list

    def to_dict(self) -> dict:
        return {
            "object_value": self.object_value,
            "field_type": self.field_type,
            "risk_score": self.risk_score,
            "level": self.level,
            "reasons": self.reasons,
        }


class RiskEngine:

    CRITICAL_THRESHOLD = 0.75
    SUSPICIOUS_THRESHOLD = 0.45

    def evaluate(self, obj: KnowledgeObject) -> RiskResult:
        sensitivity = FIELD_SENSITIVITY.get(obj.field_type, 0.2)
        confidence_gap = 1.0 - obj.confidence.final
        frequency_penalty = self._frequency_penalty(obj)

        risk_score = round(sensitivity * confidence_gap * frequency_penalty, 2)
        level = self._level(risk_score)
        reasons = self._reasons(obj, sensitivity, confidence_gap)

        result = RiskResult(
            object_value=obj.value,
            field_type=obj.field_type.value,
            risk_score=risk_score,
            level=level,
            reasons=reasons,
        )

        if level in ("critical", "suspicious"):
            bus.publish(
                Event(
                    event_type=EventType.CONFLICT_DETECTED,
                    payload=result.to_dict(),
                    source="risk_engine",
                )
            )

        return result

    def evaluate_batch(self, objects: list[KnowledgeObject]) -> list[RiskResult]:
        return [self.evaluate(obj) for obj in objects]

    def _frequency_penalty(self, obj: KnowledgeObject) -> float:
        if obj.state == KnowledgeState.CONFLICTED:
            return 2.0
        if obj.state == KnowledgeState.EXPIRED:
            return 1.5
        return 1.0

    def _level(self, score: float) -> str:
        if score >= self.CRITICAL_THRESHOLD:
            return "critical"
        if score >= self.SUSPICIOUS_THRESHOLD:
            return "suspicious"
        return "low"

    def _reasons(
        self, obj: KnowledgeObject, sensitivity: float, confidence_gap: float
    ) -> list:
        reasons = []
        if sensitivity >= 0.8:
            reasons.append(f"high sensitivity field: {obj.field_type.value}")
        if confidence_gap >= 0.3:
            reasons.append(f"low confidence: {obj.confidence.final}")
        if obj.state == KnowledgeState.CONFLICTED:
            reasons.append("object is in conflicted state")
        if obj.state == KnowledgeState.EXPIRED:
            reasons.append("object is expired")
        if obj.is_expired():
            reasons.append("object passed valid_to date")
        return reasons
