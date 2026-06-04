from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from audit.audit_event import AuditEvent
from audit.audit_event_type import AuditEventType

from core.types import EntityId


class AuditRecorder(Protocol):

    def record(
        self,
        event_type: AuditEventType,
        entity_id: EntityId | None,
        payload: Mapping[str, object],
        occurred_at: datetime,
        success: bool = True,
        error: str | None = None,
    ) -> AuditEvent: ...
