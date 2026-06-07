from __future__ import annotations

from audit.audit_chain import AuditChain
from audit.audit_entry import AuditEntry
from audit.audit_verifier import AuditVerifier
from audit.integrity_result import IntegrityViolation
from audit.verification_result import VerificationResult
from core.types import EntityId
from ui.services.api_client import get_audit_query
from ui.viewmodels.audit_models import (
    AuditEntryDetail,
    AuditEntrySummary,
    AuditVerificationSummary,
    ViolationSummary,
)

_SECRET_KEY: bytes = b"nasmi_mock_audit_secret_key_32b!"
_VERIFIER: AuditVerifier = AuditVerifier(_SECRET_KEY)


def _active_entity_id() -> EntityId | None:
    try:
        from ui.state import session_manager as sm
        from ui.state.session_keys import SessionKeys

        val = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
        return EntityId(str(val)) if val is not None else None
    except Exception:
        return None


def _to_summary(entry: AuditEntry) -> AuditEntrySummary:
    return AuditEntrySummary(
        audit_id=entry.audit_id,
        event_type=entry.event_type,
        occurred_at=entry.occurred_at,
        message=entry.message,
        actor=entry.actor,
    )


def _to_detail(entry: AuditEntry) -> AuditEntryDetail:
    return AuditEntryDetail(
        audit_id=entry.audit_id,
        event_type=entry.event_type,
        occurred_at=entry.occurred_at,
        message=entry.message,
        actor=entry.actor,
        job_id=entry.job_id,
        subject_id=entry.subject_id,
        previous_hash=entry.previous_hash,
        entry_hash=entry.entry_hash,
        metadata=dict(entry.metadata),
    )


def _to_violation_summary(v: IntegrityViolation) -> ViolationSummary:
    return ViolationSummary(
        kind=v.kind.value,
        index=v.index,
        detail=v.detail,
    )


def _to_verification_summary(result: VerificationResult) -> AuditVerificationSummary:
    return AuditVerificationSummary(
        is_valid=result.is_valid,
        verified_at=result.verified_at,
        chain_length=result.chain_length,
        verified_entries=result.verified_entries,
        violations=tuple(
            _to_violation_summary(v) for v in result.integrity_result.violations
        ),
    )


class AuditVM:

    def load_chain(self) -> AuditChain:
        try:
            entity_id = _active_entity_id()
            if entity_id is None:
                return AuditChain.empty()
            return get_audit_query().get_chain(entity_id)
        except Exception:
            return AuditChain.empty()

    def verify_chain(self, chain: AuditChain) -> VerificationResult:
        try:
            return _VERIFIER.verify(chain)
        except Exception:
            return _VERIFIER.verify(AuditChain.empty())

    def refresh(self) -> tuple[AuditChain, VerificationResult]:
        chain = self.load_chain()
        result = self.verify_chain(chain)
        return chain, result

    def get_summaries(self, chain: AuditChain) -> list[AuditEntrySummary]:
        return [_to_summary(e) for e in chain]

    def get_details(self, chain: AuditChain) -> list[AuditEntryDetail]:
        return [_to_detail(e) for e in chain]

    def get_verification_summary(
        self, result: VerificationResult
    ) -> AuditVerificationSummary:
        return _to_verification_summary(result)
