from __future__ import annotations

from core.types import EntityId
from knowledge.fact import FactStatus
from ui.services.api_client import get_knowledge_query, get_profile_query
from ui.viewmodels.profile_models import (
    FactSource,
    ProfileFact,
    ProfileSnapshot,
)
from ui.viewmodels.profile_models import (
    FactStatus as UIFactStatus,
)


def _map_fact_status(domain_status: FactStatus) -> UIFactStatus:
    mapping: dict[FactStatus, UIFactStatus] = {
        FactStatus.ACCEPTED: UIFactStatus.CONFIRMED,
        FactStatus.PENDING: UIFactStatus.UNVERIFIED,
        FactStatus.REJECTED: UIFactStatus.UNVERIFIED,
        FactStatus.SUPERSEDED: UIFactStatus.UNVERIFIED,
    }
    return mapping.get(domain_status, UIFactStatus.UNVERIFIED)


def _count_conflicts(snapshot: ProfileSnapshot) -> int:
    return sum(1 for f in snapshot.facts if f.status is UIFactStatus.CONFLICTED)


class ProfileVM:

    def load_profile(self, entity_id: str) -> ProfileSnapshot | None:
        try:
            eid = EntityId(entity_id)
            profile = get_profile_query().get_profile(eid)
            display_name = profile.display_name if profile else entity_id
            completeness = float(profile.completeness) if profile else 0.0

            facts = get_knowledge_query().list_accepted_facts(eid)
            if not facts and profile is None:
                return None

            ui_facts = tuple(
                ProfileFact(
                    fact_id=str(f.fact_id),
                    field=f.field_name,
                    value=f.display_value or str(f.canonical_value),
                    status=_map_fact_status(f.status),
                    sources=(
                        FactSource(
                            document_id=str(f.metadata.get("source_document_id", "")),
                            document_type=str(
                                f.metadata.get("source_type", f.source_stage)
                            ),
                            excerpt=str(f.metadata.get("excerpt", "")),
                            confidence=f.confidence,
                        ),
                    ),
                )
                for f in facts
            )

            return ProfileSnapshot(
                entity_id=entity_id,
                entity_name=display_name,
                confidence=completeness,
                facts=ui_facts,
            )

        except Exception:
            return None

    def refresh_profile(self, entity_id: str) -> ProfileSnapshot | None:
        return self.load_profile(entity_id)

    def count_conflicts(self, snapshot: ProfileSnapshot) -> int:
        return _count_conflicts(snapshot)
