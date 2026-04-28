from dataclasses import dataclass, field
from knowledge.knowledge_objects import KnowledgeObject, FieldType, Confidence
from cognitive.identity_graph import IdentityGraph
from cognitive.life_event_cluster import LifeEventCluster, LifeEvent
from core.events import Event, EventType
from core.event_bus import bus


FIELD_WEIGHT: dict[FieldType, float] = {
    FieldType.IDENTITY: 1.0,
    FieldType.LEGAL: 0.9,
    FieldType.FINANCIAL: 0.8,
    FieldType.EMPLOYMENT: 0.7,
    FieldType.ADDRESS: 0.6,
    FieldType.DOCUMENT: 0.5,
    FieldType.CONTACT: 0.4,
    FieldType.OTHER: 0.2,
}


@dataclass
class FusedContext:
    owner_id: str
    objects: list[KnowledgeObject]
    clusters: list[LifeEvent]
    graph_summary: dict
    trust_score: float
    coverage: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "owner_id": self.owner_id,
            "object_count": len(self.objects),
            "trust_score": self.trust_score,
            "coverage": self.coverage,
            "clusters": [c.to_dict() for c in self.clusters],
            "graph": self.graph_summary,
        }


class ContextFusion:

    def __init__(self, owner_id: str):
        self._owner_id: str = owner_id
        self._graph: IdentityGraph = IdentityGraph(owner_id)
        self._cluster: LifeEventCluster = LifeEventCluster()

    def fuse(self, objects: list[KnowledgeObject]) -> FusedContext:
        self._graph.add_batch(objects)
        clusters = self._cluster.cluster(objects)
        trust_score = self._compute_trust(objects)
        coverage = self._compute_coverage(objects)
        graph_summary = self._graph.summary()

        ctx = FusedContext(
            owner_id=self._owner_id,
            objects=objects,
            clusters=clusters,
            graph_summary=graph_summary,
            trust_score=trust_score,
            coverage=coverage,
        )

        bus.publish(
            Event(
                event_type=EventType.PREDICTION_GENERATED,
                payload=ctx.to_dict(),
                source="context_fusion",
            )
        )

        return ctx

    def _compute_trust(self, objects: list[KnowledgeObject]) -> float:
        if not objects:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for obj in objects:
            w = FIELD_WEIGHT.get(obj.field_type, 0.2)
            weighted_sum += obj.confidence.final * w
            total_weight += w

        return round(weighted_sum / total_weight, 3) if total_weight else 0.0

    def _compute_coverage(self, objects: list[KnowledgeObject]) -> dict[str, int]:
        coverage: dict[str, int] = {}
        for obj in objects:
            key = obj.field_type.value
            coverage[key] = coverage.get(key, 0) + 1
        return coverage
