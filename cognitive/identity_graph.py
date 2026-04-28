from dataclasses import dataclass, field
from datetime import datetime, timezone
from knowledge.knowledge_objects import KnowledgeObject, FieldType
from core.events import Event, EventType
from core.event_bus import bus


@dataclass
class GraphNode:
    entity_id: str
    field_type: str
    value: str
    confidence: float
    tags: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "field_type": self.field_type,
            "value": self.value,
            "confidence": self.confidence,
            "tags": list(self.tags),
        }


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
        }


FIELD_RELATIONS: dict[tuple, str] = {
    (FieldType.IDENTITY, FieldType.ADDRESS): "lives_at",
    (FieldType.IDENTITY, FieldType.EMPLOYMENT): "works_at",
    (FieldType.IDENTITY, FieldType.FINANCIAL): "owns_account",
    (FieldType.IDENTITY, FieldType.CONTACT): "reachable_via",
    (FieldType.EMPLOYMENT, FieldType.FINANCIAL): "salary_to",
    (FieldType.LEGAL, FieldType.IDENTITY): "legally_bound_to",
}


class IdentityGraph:

    def __init__(self, owner_id: str):
        self._owner_id: str = owner_id
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []

    def add_object(self, obj: KnowledgeObject) -> GraphNode:
        node = GraphNode(
            entity_id=obj.id,
            field_type=obj.field_type.value,
            value=obj.value,
            confidence=obj.confidence.final,
            tags=set(obj.tags) if obj.tags else set(),
        )
        self._nodes[node.entity_id] = node
        self._link_to_existing(obj)
        return node

    def add_batch(self, objects: list[KnowledgeObject]) -> None:
        for obj in objects:
            self.add_object(obj)

    def edges_for(self, entity_id: str) -> list[GraphEdge]:
        return [
            e
            for e in self._edges
            if e.source_id == entity_id or e.target_id == entity_id
        ]

    def neighbors(self, entity_id: str) -> list[GraphNode]:
        related_ids = set()
        for edge in self.edges_for(entity_id):
            related_ids.add(edge.source_id)
            related_ids.add(edge.target_id)
        related_ids.discard(entity_id)
        return [self._nodes[i] for i in related_ids if i in self._nodes]

    def summary(self) -> dict:
        return {
            "owner_id": self._owner_id,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }

    def _link_to_existing(self, incoming: KnowledgeObject) -> None:
        for node in self._nodes.values():
            if node.entity_id == incoming.id:
                continue

            existing_type = FieldType(node.field_type)
            relation = FIELD_RELATIONS.get(
                (existing_type, incoming.field_type)
            ) or FIELD_RELATIONS.get((incoming.field_type, existing_type))

            if relation:
                edge = GraphEdge(
                    source_id=node.entity_id,
                    target_id=incoming.id,
                    relation=relation,
                    weight=round((node.confidence + incoming.confidence.final) / 2, 2),
                )
                self._edges.append(edge)

                bus.publish(
                    Event(
                        event_type=EventType.ENTITY_MERGED,
                        payload=edge.to_dict(),
                        source="identity_graph",
                    )
                )
