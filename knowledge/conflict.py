from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_conflict_id,
    is_valid_conflict_id,
    is_valid_entity_id,
    is_valid_fact_id,
)
from core.time import is_valid_timestamp, parse_timestamp, utcnow_iso
from core.types import ConflictId, EntityId, FactId


class ConflictStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class Conflict:
    conflict_id: ConflictId
    entity_id: EntityId
    field_name: str
    fact_ids: tuple[FactId, ...]
    status: ConflictStatus
    created_at: str
    resolved_fact_id: FactId | None = field(default=None)
    resolution_note: str = field(default="")
    resolved_by: str | None = field(default=None)
    resolved_at: str | None = field(default=None)

    def __post_init__(self) -> None:
        require(
            is_valid_conflict_id(self.conflict_id),
            f"invalid conflict_id: {self.conflict_id!r}",
        )
        require(
            is_valid_entity_id(self.entity_id),
            f"invalid entity_id: {self.entity_id!r}",
        )
        require(
            isinstance(self.field_name, str) and bool(self.field_name.strip()),
            "field_name must be a non-empty string",
        )
        require(
            isinstance(self.fact_ids, tuple) and len(self.fact_ids) >= 2,
            "fact_ids must be a tuple of at least 2 FactId values",
        )
        require(
            all(is_valid_fact_id(fid) for fid in self.fact_ids),
            "all fact_ids must be valid FactId values",
        )
        require(
            len(self.fact_ids) == len(set(self.fact_ids)),
            "fact_ids must not contain duplicates",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        require(
            isinstance(self.resolution_note, str),
            "resolution_note must be a string",
        )
        if self.status is ConflictStatus.RESOLVED:
            require(
                self.resolved_fact_id is not None,
                "resolved_fact_id required when status is RESOLVED",
            )
            assert self.resolved_fact_id is not None
            require(
                is_valid_fact_id(self.resolved_fact_id),
                f"invalid resolved_fact_id: {self.resolved_fact_id!r}",
            )
            require(
                self.resolved_fact_id in self.fact_ids,
                "resolved_fact_id must be one of the conflicting fact_ids",
            )
            require(
                self.resolved_at is not None,
                "resolved_at required when status is RESOLVED",
            )
            assert self.resolved_at is not None
            require(
                is_valid_timestamp(self.resolved_at),
                f"invalid resolved_at: {self.resolved_at!r}",
            )
            require(
                parse_timestamp(self.resolved_at) >= parse_timestamp(self.created_at),
                "resolved_at cannot be earlier than created_at",
            )
            require(
                self.resolved_by is not None,
                "resolved_by required when status is RESOLVED",
            )
            assert self.resolved_by is not None
            require(
                isinstance(self.resolved_by, str) and bool(self.resolved_by.strip()),
                "resolved_by must be a non-empty string",
            )
        elif self.status is ConflictStatus.DISMISSED:
            require(
                self.resolved_fact_id is None,
                "resolved_fact_id must be None when status is DISMISSED",
            )
            require(
                self.resolved_at is not None,
                "resolved_at required when status is DISMISSED",
            )
            assert self.resolved_at is not None
            require(
                is_valid_timestamp(self.resolved_at),
                f"invalid resolved_at: {self.resolved_at!r}",
            )
            require(
                parse_timestamp(self.resolved_at) >= parse_timestamp(self.created_at),
                "resolved_at cannot be earlier than created_at",
            )
            require(
                self.resolved_by is not None,
                "resolved_by required when status is DISMISSED",
            )
            assert self.resolved_by is not None
            require(
                isinstance(self.resolved_by, str) and bool(self.resolved_by.strip()),
                "resolved_by must be a non-empty string",
            )
        else:
            require(
                self.resolved_fact_id is None,
                "resolved_fact_id must be None when status is OPEN",
            )
            require(
                self.resolved_at is None,
                "resolved_at must be None when status is OPEN",
            )
            require(
                self.resolved_by is None,
                "resolved_by must be None when status is OPEN",
            )

    def resolve(
        self,
        resolved_fact_id: FactId,
        resolved_by: str,
        resolution_note: str = "",
    ) -> Conflict:
        require(
            self.status is ConflictStatus.OPEN,
            f"only OPEN conflicts can be resolved, got {self.status!r}",
        )
        require(
            is_valid_fact_id(resolved_fact_id),
            f"invalid resolved_fact_id: {resolved_fact_id!r}",
        )
        require(
            resolved_fact_id in self.fact_ids,
            "resolved_fact_id must be one of the conflicting fact_ids",
        )
        require(
            isinstance(resolved_by, str) and bool(resolved_by.strip()),
            "resolved_by must be a non-empty string",
        )
        require(
            isinstance(resolution_note, str),
            "resolution_note must be a string",
        )
        return Conflict(
            conflict_id=self.conflict_id,
            entity_id=self.entity_id,
            field_name=self.field_name,
            fact_ids=self.fact_ids,
            status=ConflictStatus.RESOLVED,
            created_at=self.created_at,
            resolved_fact_id=resolved_fact_id,
            resolution_note=resolution_note,
            resolved_by=resolved_by,
            resolved_at=utcnow_iso(),
        )

    def dismiss(
        self,
        resolved_by: str,
        resolution_note: str = "",
    ) -> Conflict:
        require(
            self.status is ConflictStatus.OPEN,
            f"only OPEN conflicts can be dismissed, got {self.status!r}",
        )
        require(
            isinstance(resolved_by, str) and bool(resolved_by.strip()),
            "resolved_by must be a non-empty string",
        )
        require(
            isinstance(resolution_note, str),
            "resolution_note must be a string",
        )
        return Conflict(
            conflict_id=self.conflict_id,
            entity_id=self.entity_id,
            field_name=self.field_name,
            fact_ids=self.fact_ids,
            status=ConflictStatus.DISMISSED,
            created_at=self.created_at,
            resolved_fact_id=None,
            resolution_note=resolution_note,
            resolved_by=resolved_by,
            resolved_at=utcnow_iso(),
        )

    @property
    def is_open(self) -> bool:
        return self.status is ConflictStatus.OPEN

    @property
    def is_terminal(self) -> bool:
        return self.status in (ConflictStatus.RESOLVED, ConflictStatus.DISMISSED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "fact_ids": list(self.fact_ids),
            "status": str(self.status),
            "created_at": self.created_at,
            "resolved_fact_id": self.resolved_fact_id,
            "resolution_note": self.resolution_note,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Conflict:
        return cls(
            conflict_id=ConflictId(data["conflict_id"]),
            entity_id=EntityId(data["entity_id"]),
            field_name=data["field_name"],
            fact_ids=tuple(FactId(fid) for fid in data["fact_ids"]),
            status=ConflictStatus(data["status"]),
            created_at=data["created_at"],
            resolved_fact_id=(
                FactId(data["resolved_fact_id"])
                if data.get("resolved_fact_id")
                else None
            ),
            resolution_note=data.get("resolution_note", ""),
            resolved_by=data.get("resolved_by"),
            resolved_at=data.get("resolved_at"),
        )

    @classmethod
    def create(
        cls,
        entity_id: str,
        field_name: str,
        fact_ids: list[str],
    ) -> Conflict:
        require(
            is_valid_entity_id(entity_id),
            f"invalid entity_id: {entity_id!r}",
        )
        require(
            isinstance(field_name, str) and bool(field_name.strip()),
            "field_name must be a non-empty string",
        )
        require(
            isinstance(fact_ids, list) and len(fact_ids) >= 2,
            "fact_ids must be a list of at least 2 FactId values",
        )
        require(
            all(is_valid_fact_id(fid) for fid in fact_ids),
            "all fact_ids must be valid FactId values",
        )
        require(
            len(fact_ids) == len(set(fact_ids)),
            "fact_ids must not contain duplicates",
        )
        return cls(
            conflict_id=generate_conflict_id(),
            entity_id=EntityId(entity_id),
            field_name=field_name,
            fact_ids=tuple(FactId(fid) for fid in fact_ids),
            status=ConflictStatus.OPEN,
            created_at=utcnow_iso(),
            resolved_fact_id=None,
            resolution_note="",
            resolved_by=None,
            resolved_at=None,
        )
