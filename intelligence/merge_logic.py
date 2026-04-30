from __future__ import annotations
from dataclasses import dataclass, field
from intelligence.ner_engine import ExtractedEntities
from core.events import Event, EventType
from core.event_bus import bus
from db.database import Database
from db.models import ContradictionModel, AuditLogModel

_con = ContradictionModel()
_al  = AuditLogModel()

FIELD_PRIORITY = [
    'passport_number',
    'id_number',
    'full_name',
    'date_of_birth',
    'nationality',
    'address',
    'phone',
    'email',
    'employer',
    'issue_date',
    'expiry_date',
    'document_type',
]


@dataclass
class MergeResult:
    merged:    ExtractedEntities
    conflicts: dict = field(default_factory=dict)
    sources:   list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'merged':    self.merged.to_dict(),
            'conflicts': self.conflicts,
            'sources':   self.sources,
        }


class MergeLogic:

    CONFIDENCE_THRESHOLD = 0.85

    def merge(
        self,
        entities_list: list[ExtractedEntities],
        sources: list[str],
    ) -> MergeResult:
        merged    = ExtractedEntities()
        conflicts = {}

        for field_name in FIELD_PRIORITY:
            winner, conflict = self._resolve(field_name, entities_list, sources)
            if winner is not None:
                setattr(merged, field_name, winner)
            if conflict:
                conflicts[field_name] = conflict

        merged.extra      = self._merge_extras(entities_list)
        merged.confidence = self._avg_confidence(entities_list)

        result = MergeResult(merged=merged, conflicts=conflicts, sources=sources)

        if conflicts:
            self._save_conflicts(conflicts, sources)

        bus.publish(
            Event(
                event_type=EventType.CONFLICT_DETECTED if conflicts else EventType.ENTITY_MERGED,
                payload=result.to_dict(),
                source='merge_logic',
            )
        )

        return result

    # ── DB Write ───────────────────────────────────────────────────────────

    def _save_conflicts(self, conflicts: dict, sources: list[str]) -> None:
        src_a = sources[0] if len(sources) > 0 else 'unknown'
        src_b = sources[1] if len(sources) > 1 else 'unknown'

        try:
            with Database() as db:
                with db.transaction():
                    for field_name, values in conflicts.items():
                        vals  = list(values.values())
                        val_a = str(vals[0]) if len(vals) > 0 else '—'
                        val_b = str(vals[1]) if len(vals) > 1 else '—'

                        con_id = _con.insert(
                            db,
                            field=field_name,
                            value_a=val_a,
                            value_b=val_b,
                            source_a=src_a,
                            source_b=src_b,
                        )

                        _al.log(
                            db,
                            action='conflict_detected',
                            table_name='contradictions',
                            record_id=int(con_id or 0),
                            performed_by='merge_logic',
                            details=f'{field_name}: "{val_a}" vs "{val_b}"',
                        )
        except Exception:
            pass

    # ── Resolution ─────────────────────────────────────────────────────────
    
    def _resolve(
        self,
        field_name: str,
        entities_list: list[ExtractedEntities],
        sources: list[str],
        
    )-> tuple:
        values = {}
        for i, entity in enumerate(entities_list):
            val = getattr(entity, field_name, None)
            if val:
                source_key = sources[i] if i < len(sources) else f'source_{i}'
                values[source_key] = val

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
        best_val   = None
        best_score = -1.0
        for entity in entities_list:
            val = getattr(entity, field_name, None)
            if val and entity.confidence > best_score:
                best_score = entity.confidence
                best_val   = val
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