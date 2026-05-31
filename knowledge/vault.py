from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_vault_id,
    is_valid_entity_id,
    is_valid_vault_id,
)
from core.time import is_valid_timestamp, utcnow_iso
from core.types import ConflictId, EntityId, FactId, VaultId
from knowledge.conflict import Conflict, ConflictStatus
from knowledge.entity import Entity
from knowledge.profile import Profile


@dataclass(frozen=True)
class Vault:
    vault_id: VaultId
    entities: dict[EntityId, Entity]
    profiles: dict[EntityId, Profile]
    conflicts: dict[ConflictId, Conflict]
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(
            is_valid_vault_id(self.vault_id),
            f"invalid vault_id: {self.vault_id!r}",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        require(
            isinstance(self.entities, dict),
            "entities must be a dictionary",
        )
        require(
            isinstance(self.profiles, dict),
            "profiles must be a dictionary",
        )
        require(
            isinstance(self.conflicts, dict),
            "conflicts must be a dictionary",
        )
        require(
            isinstance(self.metadata, dict),
            "metadata must be a dictionary",
        )
        require(
            all(isinstance(e, Entity) for e in self.entities.values()),
            "all entities values must be Entity instances",
        )
        require(
            all(k == e.entity_id for k, e in self.entities.items()),
            "each entities key must match Entity.entity_id",
        )
        require(
            all(isinstance(p, Profile) for p in self.profiles.values()),
            "all profiles values must be Profile instances",
        )
        require(
            all(k == p.entity_id for k, p in self.profiles.items()),
            "each profiles key must match Profile.entity_id",
        )
        require(
            all(k in self.entities for k in self.profiles),
            "all profile entity_ids must reference existing entities",
        )
        require(
            all(isinstance(c, Conflict) for c in self.conflicts.values()),
            "all conflicts values must be Conflict instances",
        )
        require(
            all(k == c.conflict_id for k, c in self.conflicts.items()),
            "each conflicts key must match Conflict.conflict_id",
        )
        require(
            all(c.entity_id in self.entities for c in self.conflicts.values()),
            "all conflict entity_ids must reference existing entities",
        )

    def add_entity(self, entity: Entity) -> Vault:
        require(
            isinstance(entity, Entity),
            "entity must be an Entity instance",
        )
        require(
            entity.entity_id not in self.entities,
            f"entity already exists: {entity.entity_id!r}",
        )
        return Vault(
            vault_id=self.vault_id,
            entities={**self.entities, entity.entity_id: entity},
            profiles=dict(self.profiles),
            conflicts=dict(self.conflicts),
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def remove_entity(self, entity_id: EntityId) -> Vault:
        require(
            is_valid_entity_id(entity_id),
            f"invalid entity_id: {entity_id!r}",
        )
        require(
            entity_id in self.entities,
            f"entity not found: {entity_id!r}",
        )
        require(
            entity_id not in self.profiles,
            f"cannot remove entity with existing profile: {entity_id!r}",
        )
        require(
            not any(c.entity_id == entity_id for c in self.conflicts.values()),
            f"cannot remove entity with conflict history: {entity_id!r}",
        )
        return Vault(
            vault_id=self.vault_id,
            entities={k: v for k, v in self.entities.items() if k != entity_id},
            profiles=dict(self.profiles),
            conflicts=dict(self.conflicts),
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def update_profile(self, profile: Profile) -> Vault:
        require(
            isinstance(profile, Profile),
            "profile must be a Profile instance",
        )
        require(
            profile.entity_id in self.entities,
            f"entity not found for profile: {profile.entity_id!r}",
        )
        return Vault(
            vault_id=self.vault_id,
            entities=dict(self.entities),
            profiles={**self.profiles, profile.entity_id: profile},
            conflicts=dict(self.conflicts),
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def remove_profile(self, entity_id: EntityId) -> Vault:
        require(
            is_valid_entity_id(entity_id),
            f"invalid entity_id: {entity_id!r}",
        )
        require(
            entity_id in self.entities,
            f"entity not found: {entity_id!r}",
        )
        require(
            entity_id in self.profiles,
            f"no profile found for entity: {entity_id!r}",
        )
        return Vault(
            vault_id=self.vault_id,
            entities=dict(self.entities),
            profiles={k: v for k, v in self.profiles.items() if k != entity_id},
            conflicts=dict(self.conflicts),
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def register_conflict(self, conflict: Conflict) -> Vault:
        require(
            isinstance(conflict, Conflict),
            "conflict must be a Conflict instance",
        )
        require(
            conflict.entity_id in self.entities,
            f"entity not found for conflict: {conflict.entity_id!r}",
        )
        require(
            conflict.conflict_id not in self.conflicts,
            f"conflict already registered: {conflict.conflict_id!r}",
        )
        return Vault(
            vault_id=self.vault_id,
            entities=dict(self.entities),
            profiles=dict(self.profiles),
            conflicts={**self.conflicts, conflict.conflict_id: conflict},
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def resolve_conflict(
        self,
        conflict_id: ConflictId,
        resolved_fact_id: FactId,
        resolved_by: str,
        resolution_note: str = "",
    ) -> Vault:
        require(
            conflict_id in self.conflicts,
            f"conflict not found: {conflict_id!r}",
        )
        resolved = self.conflicts[conflict_id].resolve(
            resolved_fact_id=resolved_fact_id,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
        )
        return Vault(
            vault_id=self.vault_id,
            entities=dict(self.entities),
            profiles=dict(self.profiles),
            conflicts={**self.conflicts, conflict_id: resolved},
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def dismiss_conflict(
        self,
        conflict_id: ConflictId,
        resolved_by: str,
        resolution_note: str = "",
    ) -> Vault:
        require(
            conflict_id in self.conflicts,
            f"conflict not found: {conflict_id!r}",
        )
        dismissed = self.conflicts[conflict_id].dismiss(
            resolved_by=resolved_by,
            resolution_note=resolution_note,
        )
        return Vault(
            vault_id=self.vault_id,
            entities=dict(self.entities),
            profiles=dict(self.profiles),
            conflicts={**self.conflicts, conflict_id: dismissed},
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def remove_conflict(self, conflict_id: ConflictId) -> Vault:
        require(
            conflict_id in self.conflicts,
            f"conflict not found: {conflict_id!r}",
        )
        require(
            self.conflicts[conflict_id].is_terminal,
            f"only terminal conflicts can be removed: {conflict_id!r}",
        )
        return Vault(
            vault_id=self.vault_id,
            entities=dict(self.entities),
            profiles=dict(self.profiles),
            conflicts={k: v for k, v in self.conflicts.items() if k != conflict_id},
            created_at=self.created_at,
            metadata=dict(self.metadata),
        )

    def get_entity(self, entity_id: EntityId) -> Entity | None:
        return self.entities.get(entity_id)

    def get_profile(self, entity_id: EntityId) -> Profile | None:
        return self.profiles.get(entity_id)

    def get_conflict(self, conflict_id: ConflictId) -> Conflict | None:
        return self.conflicts.get(conflict_id)

    def has_entity(self, entity_id: EntityId) -> bool:
        return entity_id in self.entities

    def has_profile(self, entity_id: EntityId) -> bool:
        return entity_id in self.profiles

    def open_conflicts(self) -> tuple[Conflict, ...]:
        return tuple(
            c for c in self.conflicts.values() if c.status is ConflictStatus.OPEN
        )

    def entity_conflicts(self, entity_id: EntityId) -> tuple[Conflict, ...]:
        return tuple(c for c in self.conflicts.values() if c.entity_id == entity_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "profiles": {k: v.to_dict() for k, v in self.profiles.items()},
            "conflicts": {k: v.to_dict() for k, v in self.conflicts.items()},
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vault:
        return cls(
            vault_id=VaultId(data["vault_id"]),
            entities={
                EntityId(k): Entity.from_dict(v) for k, v in data["entities"].items()
            },
            profiles={
                EntityId(k): Profile.from_dict(v) for k, v in data["profiles"].items()
            },
            conflicts={
                ConflictId(k): Conflict.from_dict(v)
                for k, v in data["conflicts"].items()
            },
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        metadata: dict[str, Any] | None = None,
    ) -> Vault:
        return cls(
            vault_id=generate_vault_id(),
            entities={},
            profiles={},
            conflicts={},
            created_at=utcnow_iso(),
            metadata=dict(metadata) if metadata else {},
        )
