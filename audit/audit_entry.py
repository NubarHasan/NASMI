from __future__ import annotations

import copy
import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.identifiers import generate_audit_id
from core.time import format_timestamp, parse_timestamp, utcnow
from core.types import AuditId, EntityId, JobId

_SECRET_KEY_MIN_BYTES = 32


class AuditEventType(StrEnum):
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_RETRYING = "job_retrying"

    DOCUMENT_IMPORTED = "document_imported"
    OCR_COMPLETED = "ocr_completed"

    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"

    CONFLICT_CREATED = "conflict_created"
    CONFLICT_RESOLVED = "conflict_resolved"
    FACT_ACCEPTED = "fact_accepted"
    KNOWLEDGE_UPDATED = "knowledge_updated"

    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"

    PACKAGE_GENERATED = "package_generated"
    PACKAGE_ASSEMBLED = "package_assembled"
    PACKAGE_EXPORTED = "package_exported"

    INTEGRITY_VERIFIED = "integrity_verified"


_JSON_PRIMITIVES = (str, int, float, bool, type(None))


def _assert_json_primitives(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError(f"metadata key at '{path}' must be str, got {type(k)}")
            _assert_json_primitives(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _assert_json_primitives(v, f"{path}[{i}]")
    elif not isinstance(value, _JSON_PRIMITIVES):
        raise ValueError(
            f"metadata value at '{path}' must be a JSON primitive, got {type(value)}"
        )


def _validated_meta(raw: Any) -> dict[str, Any]:
    require(isinstance(raw, dict), "metadata must be a dictionary")
    meta: dict[str, Any] = copy.deepcopy(raw)
    _assert_json_primitives(meta, "metadata")
    return meta


def _canonical_payload(
    audit_id: AuditId,
    event_type: AuditEventType,
    job_id: JobId | None,
    subject_id: EntityId | None,
    occurred_at: datetime,
    actor: str | None,
    message: str,
    metadata: Mapping[str, Any],
    previous_hash: str | None,
) -> bytes:
    payload: dict[str, Any] = {
        "audit_id": str(audit_id),
        "event_type": str(event_type),
        "job_id": str(job_id) if job_id is not None else None,
        "subject_id": str(subject_id) if subject_id is not None else None,
        "occurred_at": format_timestamp(occurred_at),
        "actor": actor,
        "message": message,
        "metadata": {k: v for k, v in metadata.items()},
        "previous_hash": previous_hash,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _compute_hmac(secret_key: bytes, payload: bytes) -> str:
    return hmac.new(secret_key, payload, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    audit_id: AuditId
    event_type: AuditEventType
    job_id: JobId | None
    subject_id: EntityId | None
    occurred_at: datetime
    actor: str | None
    message: str
    metadata: Mapping[str, Any]
    previous_hash: str | None
    entry_hash: str

    def __post_init__(self) -> None:
        require(bool(self.audit_id), "audit_id must be non-empty")
        require(
            isinstance(self.event_type, AuditEventType),
            "event_type must be an AuditEventType",
        )
        require(
            self.job_id is None or bool(self.job_id),
            "job_id must be non-empty when provided",
        )
        require(
            self.subject_id is None or bool(self.subject_id),
            "subject_id must be non-empty when provided",
        )
        require(
            self.job_id is not None or self.subject_id is not None,
            "at least one of job_id or subject_id must be provided",
        )
        require(
            isinstance(self.occurred_at, datetime), "occurred_at must be a datetime"
        )
        require(
            self.actor is None or bool(self.actor),
            "actor must be non-empty when provided",
        )
        require(bool(self.message), "message must be non-empty")
        require(bool(self.entry_hash), "entry_hash must be non-empty")
        require(
            isinstance(self.metadata, MappingProxyType),
            "metadata must be a MappingProxyType",
        )

    def verify(self, secret_key: bytes) -> bool:
        require(
            isinstance(secret_key, bytes) and len(secret_key) >= _SECRET_KEY_MIN_BYTES,
            f"secret_key must be at least {_SECRET_KEY_MIN_BYTES} bytes",
        )
        payload = _canonical_payload(
            audit_id=self.audit_id,
            event_type=self.event_type,
            job_id=self.job_id,
            subject_id=self.subject_id,
            occurred_at=self.occurred_at,
            actor=self.actor,
            message=self.message,
            metadata=self.metadata,
            previous_hash=self.previous_hash,
        )
        expected = _compute_hmac(secret_key, payload)
        return hmac.compare_digest(self.entry_hash, expected)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "audit_id": str(self.audit_id),
            "event_type": str(self.event_type),
            "job_id": str(self.job_id) if self.job_id is not None else None,
            "subject_id": str(self.subject_id) if self.subject_id is not None else None,
            "occurred_at": format_timestamp(self.occurred_at),
            "actor": self.actor,
            "message": self.message,
            "metadata": {k: v for k, v in self.metadata.items()},
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEntry:
        meta = _validated_meta(data.get("metadata", {}))
        return cls(
            audit_id=data["audit_id"],
            event_type=AuditEventType(data["event_type"]),
            job_id=data.get("job_id"),
            subject_id=data.get("subject_id"),
            occurred_at=parse_timestamp(data["occurred_at"]),
            actor=data.get("actor"),
            message=data["message"],
            metadata=MappingProxyType(meta),
            previous_hash=data.get("previous_hash"),
            entry_hash=data["entry_hash"],
        )

    @classmethod
    def create(
        cls,
        *,
        secret_key: bytes,
        event_type: AuditEventType,
        message: str,
        job_id: JobId | None = None,
        subject_id: EntityId | None = None,
        actor: str | None = None,
        metadata: dict[str, Any] | None = None,
        previous_hash: str | None = None,
    ) -> AuditEntry:
        require(
            isinstance(secret_key, bytes) and len(secret_key) >= _SECRET_KEY_MIN_BYTES,
            f"secret_key must be at least {_SECRET_KEY_MIN_BYTES} bytes",
        )
        require(
            isinstance(event_type, AuditEventType),
            "event_type must be an AuditEventType",
        )
        require(bool(message), "message must be non-empty")
        require(
            job_id is not None or subject_id is not None,
            "at least one of job_id or subject_id must be provided",
        )

        meta = _validated_meta(metadata if metadata is not None else {})

        audit_id = generate_audit_id()
        occurred_at = utcnow()

        payload = _canonical_payload(
            audit_id=audit_id,
            event_type=event_type,
            job_id=job_id,
            subject_id=subject_id,
            occurred_at=occurred_at,
            actor=actor,
            message=message,
            metadata=meta,
            previous_hash=previous_hash,
        )
        entry_hash = _compute_hmac(secret_key, payload)

        return cls(
            audit_id=audit_id,
            event_type=event_type,
            job_id=job_id,
            subject_id=subject_id,
            occurred_at=occurred_at,
            actor=actor,
            message=message,
            metadata=MappingProxyType(meta),
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
