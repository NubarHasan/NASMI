from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from audit.audit_entry import AuditEntry, AuditEventType
from core.types import EntityId


class AuditRecorder(Protocol):

    def record(
        self,
        event_type: AuditEventType,
        subject_id: EntityId | None,
        payload: Mapping[str, object],
        occurred_at: datetime,
        success: bool = True,
        error: str | None = None,
    ) -> AuditEntry: ...
