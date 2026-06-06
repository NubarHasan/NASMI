from __future__ import annotations

from audit.audit_chain import AuditChain
from audit.audit_entry import AuditEntry, AuditEventType
from audit.audit_verifier import AuditVerifier
from audit.integrity_result import IntegrityViolation
from audit.verification_result import VerificationResult
from core.identifiers import generate_entity_id, generate_job_id
from core.types import EntityId, JobId
from ui.viewmodels.audit_models import (
    AuditEntryDetail,
    AuditEntrySummary,
    AuditVerificationSummary,
    ViolationSummary,
)

_MOCK_SECRET: bytes = b"nasmi_mock_audit_secret_key_32b!"

_MOCK_ENTITY_ID: EntityId = generate_entity_id()
_MOCK_JOB_ID: JobId = generate_job_id()


def _build_mock_chain() -> AuditChain:
    e1 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.DOCUMENT_IMPORTED,
        subject_id=_MOCK_ENTITY_ID,
        message="Document imported into the system",
        actor="system",
        metadata={"source": "upload", "pages": 12},
    )
    e2 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.OCR_COMPLETED,
        subject_id=_MOCK_ENTITY_ID,
        message="OCR processing completed successfully",
        actor="ocr_engine",
        metadata={"confidence": 0.97, "language": "ar"},
        previous_hash=e1.entry_hash,
    )
    e3 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.JOB_CREATED,
        job_id=_MOCK_JOB_ID,
        subject_id=_MOCK_ENTITY_ID,
        message="Extraction job created",
        actor="scheduler",
        metadata={"priority": "high"},
        previous_hash=e2.entry_hash,
    )
    e4 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.JOB_STARTED,
        job_id=_MOCK_JOB_ID,
        subject_id=_MOCK_ENTITY_ID,
        message="Extraction job started",
        actor="worker",
        previous_hash=e3.entry_hash,
    )
    e5 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.ENTITY_CREATED,
        subject_id=_MOCK_ENTITY_ID,
        message="Entity record created from extraction results",
        actor="extractor",
        metadata={"entity_type": "person", "fields_extracted": 8},
        previous_hash=e4.entry_hash,
    )
    e6 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.VALIDATION_PASSED,
        subject_id=_MOCK_ENTITY_ID,
        message="Entity passed all validation rules",
        actor="validator",
        metadata={"rules_checked": 14},
        previous_hash=e5.entry_hash,
    )
    e7 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.PACKAGE_GENERATED,
        job_id=_MOCK_JOB_ID,
        subject_id=_MOCK_ENTITY_ID,
        message="Output package generated",
        actor="packager",
        metadata={"format": "pdf", "size_kb": 340},
        previous_hash=e6.entry_hash,
    )
    e8 = AuditEntry.create(
        secret_key=_MOCK_SECRET,
        event_type=AuditEventType.INTEGRITY_VERIFIED,
        subject_id=_MOCK_ENTITY_ID,
        message="Chain integrity verified",
        actor="verifier",
        metadata={"verified_entries": 7},
        previous_hash=e7.entry_hash,
    )
    return AuditChain.from_entries((e1, e2, e3, e4, e5, e6, e7, e8))


_MOCK_CHAIN: AuditChain = _build_mock_chain()
_MOCK_VERIFIER: AuditVerifier = AuditVerifier(_MOCK_SECRET)


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
        return _MOCK_CHAIN

    def verify_chain(self, chain: AuditChain) -> VerificationResult:
        return _MOCK_VERIFIER.verify(chain)

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
