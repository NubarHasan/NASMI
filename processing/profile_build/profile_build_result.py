from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.guards import require
from core.identifiers import is_valid_entity_id
from core.types import EntityId
from knowledge.profile import Profile


@dataclass(frozen=True)
class ProfileBuildResult:
    entity_id: EntityId
    profile: Profile
    fields_built: int
    fields_missing: tuple[str, ...]
    completeness: float
    skipped_facts: int

    def __post_init__(self) -> None:
        require(is_valid_entity_id(self.entity_id), "invalid entity_id")
        require(isinstance(self.profile, Profile), "profile must be a Profile")
        require(self.fields_built >= 0, "fields_built must be >= 0")
        require(0.0 <= self.completeness <= 1.0, "completeness must be in [0.0, 1.0]")
        require(self.skipped_facts >= 0, "skipped_facts must be >= 0")

    @property
    def is_complete(self) -> bool:
        return self.completeness == 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "fields_built": self.fields_built,
            "fields_missing": list(self.fields_missing),
            "completeness": self.completeness,
            "skipped_facts": self.skipped_facts,
            "is_complete": self.is_complete,
        }
