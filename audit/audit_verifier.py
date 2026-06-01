from __future__ import annotations

from audit.audit_chain import AuditChain
from audit.integrity_result import (
    IntegrityResult,
    IntegrityViolation,
    ViolationKind,
)
from audit.verification_result import VerificationResult
from core.guards import require
from core.time import utcnow


class AuditVerifier:
    def __init__(self, secret_key: bytes) -> None:
        require(isinstance(secret_key, bytes), "secret_key must be bytes")
        require(len(secret_key) >= 32, "secret_key must be at least 32 bytes")
        self._secret_key = secret_key

    def verify(self, chain: AuditChain) -> VerificationResult:
        require(isinstance(chain, AuditChain), "chain must be an AuditChain")

        violations: list[IntegrityViolation] = []
        entries = chain.entries

        for i, entry in enumerate(entries):
            if not entry.verify(self._secret_key):
                violations.append(
                    IntegrityViolation(
                        kind=ViolationKind.INVALID_HMAC,
                        index=i,
                        detail=f"HMAC verification failed for entry at index {i}",
                    )
                )

        integrity_result = (
            IntegrityResult.passed()
            if not violations
            else IntegrityResult.failed(violations)
        )

        failed_indices = {v.index for v in violations}
        verified_entries = sum(
            1 for i in range(len(entries)) if i not in failed_indices
        )

        return VerificationResult(
            integrity_result=integrity_result,
            verified_at=utcnow(),
            chain_length=len(entries),
            verified_entries=verified_entries,
        )
