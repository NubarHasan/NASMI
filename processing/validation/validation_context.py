from __future__ import annotations

from dataclasses import dataclass

from core.guards import require
from knowledge.conflict import Conflict, ConflictStatus
from knowledge.entity import Entity
from knowledge.fact import Fact, FactStatus


@dataclass(frozen=True)
class ValidationContext:
    entity: Entity
    existing_facts: tuple[Fact, ...]
    accepted_facts: tuple[Fact, ...]
    open_conflicts: tuple[Conflict, ...]

    def __post_init__(self) -> None:
        require(
            isinstance(self.entity, Entity),
            "entity must be an Entity instance",
        )
        require(
            isinstance(self.existing_facts, tuple)
            and all(isinstance(f, Fact) for f in self.existing_facts),
            "existing_facts must be a tuple of Fact instances",
        )
        require(
            isinstance(self.accepted_facts, tuple)
            and all(isinstance(f, Fact) for f in self.accepted_facts),
            "accepted_facts must be a tuple of Fact instances",
        )
        require(
            all(f.status is FactStatus.ACCEPTED for f in self.accepted_facts),
            "accepted_facts must contain only ACCEPTED facts",
        )
        require(
            isinstance(self.open_conflicts, tuple)
            and all(isinstance(c, Conflict) for c in self.open_conflicts),
            "open_conflicts must be a tuple of Conflict instances",
        )
        require(
            all(c.status is ConflictStatus.OPEN for c in self.open_conflicts),
            "open_conflicts must contain only OPEN conflicts",
        )
        require(
            all(f.entity_id == self.entity.entity_id for f in self.existing_facts),
            "all existing_facts must belong to the same entity",
        )
        require(
            all(f.entity_id == self.entity.entity_id for f in self.accepted_facts),
            "all accepted_facts must belong to the same entity",
        )
        require(
            all(c.entity_id == self.entity.entity_id for c in self.open_conflicts),
            "all open_conflicts must belong to the same entity",
        )

    def accepted_for_field(self, field_name: str) -> tuple[Fact, ...]:
        require(bool(field_name.strip()), "field_name must not be blank")
        return tuple(f for f in self.accepted_facts if f.field_name == field_name)

    def conflicts_for_field(self, field_name: str) -> tuple[Conflict, ...]:
        require(bool(field_name.strip()), "field_name must not be blank")
        return tuple(c for c in self.open_conflicts if c.field_name == field_name)

    def has_accepted_value(self, field_name: str) -> bool:
        return len(self.accepted_for_field(field_name)) > 0

    def has_open_conflict(self, field_name: str) -> bool:
        return len(self.conflicts_for_field(field_name)) > 0

    @classmethod
    def create(
        cls,
        entity: Entity,
        existing_facts: tuple[Fact, ...],
        open_conflicts: tuple[Conflict, ...],
    ) -> ValidationContext:
        require(
            isinstance(existing_facts, tuple),
            "existing_facts must be a tuple",
        )
        require(
            isinstance(open_conflicts, tuple),
            "open_conflicts must be a tuple",
        )
        accepted = tuple(f for f in existing_facts if f.status is FactStatus.ACCEPTED)
        return cls(
            entity=entity,
            existing_facts=existing_facts,
            accepted_facts=accepted,
            open_conflicts=open_conflicts,
        )
