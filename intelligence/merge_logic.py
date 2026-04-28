from dataclasses import dataclass, field
from intelligence.ner_engine import ExtractedEntities
from core.events import Event, EventType
from core.event_bus import bus


FIELD_PRIORITY = [
    "passport_number",
    "id_number",
    "full_name",
    "date_of_birth",
    "nationality",
    "address",
    "phone",
    "email",
    "employer",
    "issue_date",
    "expiry_date",
    "document_type",
]


@dataclass
class MergeResult:
    merged: ExtractedEntities
    conflicts: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "merged": self.merged.to_dict(),
            "conflicts": self.conflicts,
            "sources": self.sources,
        }


class MergeLogic:

    CONFIDENCE_THRESHOLD = 0.85

    def merge(
        self, entities_list: list[ExtractedEntities], sources: list[str]
    ) -> MergeResult:
        merged = ExtractedEntities()
        conflicts = {}

        for field_name in FIELD_PRIORITY:
            winner, conflict = self._resolve(field_name, entities_list, sources)
            if winner is not None:
                setattr(merged, field_name, winner)
            if conflict:
                conflicts[field_name] = conflict

        merged.extra = self._merge_extras(entities_list)
        merged.confidence = self._avg_confidence(entities_list)

        result = MergeResult(merged=merged, conflicts=conflicts, sources=sources)

        event_type = (
            EventType.CONFLICT_DETECTED if conflicts else EventType.ENTITY_MERGED
        )

        bus.publish(
            Event(
                event_type=event_type,
                payload=result.to_dict(),
                source="merge_logic",
            )
        )

        return result

    def _resolve(
        self,
        field_name: str,
        entities_list: list[ExtractedEntities],
        sources: list[str],
    ) -> tuple:
        values = {}
        for i, entity in enumerate(entities_list):
            val = getattr(entity, field_name, None)
            if val:
                values[sources[i]] = val

        unique = set(values.values())

        if len(unique) == 0:
            return None, {}
        if len(unique) == 1:
            return unique.pop(), {}

        winner = self._pick_highest_confidence(field_name, entities_list, sources)
        return winner, values

    def _pick_highest_confidence(
        self,
        field_name: str,
        entities_list: list[ExtractedEntities],
        sources: list[str],
    ) -> str | None:
        best_val = None
        best_score = -1.0
        for i, entity in enumerate(entities_list):
            val = getattr(entity, field_name, None)
            if val and entity.confidence > best_score:
                best_score = entity.confidence
                best_val = val
        return best_val

    def _merge_extras(self, entities_list: list[ExtractedEntities]) -> dict:
        merged = {}
        for entity in entities_list:
            merged.update(entity.extra or {})
        return merged

    def _avg_confidence(self, entities_list: list[ExtractedEntities]) -> float:
        if not entities_list:
            return 0.0
        return round(sum(e.confidence for e in entities_list) / len(entities_list), 2)
