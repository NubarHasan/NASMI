from __future__ import annotations

from typing import Any

from core.guards import require
from core.identifiers import is_valid_entity_id
from core.types import EntityId
from knowledge.fact import Fact, FactStatus
from knowledge.profile import Profile, ProfileField


class ProfileBuilder:

    def __init__(
        self,
        entity_id: EntityId,
        entity_type: str,
        schema: frozenset[str],
    ) -> None:
        require(is_valid_entity_id(entity_id), f"invalid entity_id: {entity_id!r}")
        require(
            isinstance(entity_type, str) and bool(entity_type.strip()),
            "entity_type must be a non-empty string",
        )
        require(
            isinstance(schema, frozenset) and len(schema) > 0,
            "schema must be a non-empty frozenset",
        )

        self._entity_id: EntityId = entity_id
        self._entity_type: str = entity_type
        self._schema: frozenset[str] = schema
        self._fields: dict[str, ProfileField] = {}

    def add_fact(self, fact: Fact) -> ProfileBuilder:
        require(isinstance(fact, Fact), "fact must be a Fact instance")
        require(
            fact.status is FactStatus.ACCEPTED,
            f"ProfileBuilder accepts ACCEPTED facts only, got [{fact.status.value}]",
        )
        require(
            fact.entity_id == self._entity_id,
            f"fact entity_id [{fact.entity_id}] does not match "
            f"builder entity_id [{self._entity_id}]",
        )

        existing = self._fields.get(fact.field_name)

        if existing is None or fact.confidence > existing.confidence:
            self._fields[fact.field_name] = ProfileField(
                field_name=fact.field_name,
                value=fact.canonical_value,
                display_value=str(fact.canonical_value),
                confidence=fact.confidence,
                fact_id=fact.fact_id,
                sourced_at=fact.created_at,
            )

        return self

    def add_facts(self, facts: list[Fact]) -> ProfileBuilder:
        for fact in facts:
            self.add_fact(fact)
        return self

    def covered_fields(self) -> frozenset[str]:
        return frozenset(self._fields.keys())

    def missing_fields(self) -> frozenset[str]:
        return self._schema - self.covered_fields()

    def completeness(self) -> float:
        covered = len(self._schema & self.covered_fields())
        return round(covered / len(self._schema), 4)

    def build(
        self,
        display_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Profile:
        require(
            isinstance(display_name, str) and bool(display_name.strip()),
            "display_name must be a non-empty string",
        )
        require(
            len(self._fields) > 0,
            f"cannot build Profile for [{self._entity_id}] — no facts added",
        )

        return Profile.create(
            entity_id=self._entity_id,
            entity_type=self._entity_type,
            display_name=display_name,
            fields=dict(self._fields),
            completeness=self.completeness(),
            metadata=metadata,
        )
