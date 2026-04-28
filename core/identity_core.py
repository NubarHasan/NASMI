from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from core.events import Event, EventType
from core.event_bus import bus


class LockLevel(Enum):
    SOFT = "soft"
    HARD = "hard"


@dataclass
class IdentityCore:
    full_name: str
    date_of_birth: str
    nationality: str
    id_number: str
    id_type: str
    verified: bool = False
    lock_level: LockLevel = LockLevel.HARD
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _FROZEN_FIELDS = {
        "full_name",
        "date_of_birth",
        "nationality",
        "id_number",
        "id_type",
    }

    def update(self, field_name: str, value: str, force: bool = False) -> bool:
        if field_name in self._FROZEN_FIELDS:
            if self.lock_level == LockLevel.HARD and not force:
                bus.publish(
                    Event(
                        event_type=EventType.CONFLICT_DETECTED,
                        payload={"field": field_name, "attempted_value": value},
                        source="identity_core",
                    )
                )
                return False

        setattr(self, field_name, value)
        self.updated_at = datetime.now(timezone.utc)

        bus.publish(
            Event(
                event_type=EventType.IDENTITY_UPDATED,
                payload={"field": field_name, "value": value},
                source="identity_core",
            )
        )
        return True

    def verify(self) -> None:
        self.verified = True
        self.updated_at = datetime.now(timezone.utc)

    def is_frozen(self, field_name: str) -> bool:
        return field_name in self._FROZEN_FIELDS and self.lock_level == LockLevel.HARD

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth,
            "nationality": self.nationality,
            "id_number": self.id_number,
            "id_type": self.id_type,
            "verified": self.verified,
            "lock_level": self.lock_level.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
