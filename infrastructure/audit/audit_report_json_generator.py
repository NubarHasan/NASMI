from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from application.ports.audit_query import AuditQueryService
from audit.audit_chain import AuditChain
from audit.audit_verifier import AuditVerifier
from audit.integrity_result import IntegrityViolation
from audit.verification_result import VerificationResult
from core.filesystem import ensure_directory, write_atomic_text
from core.guards import require
from core.types import EntityId
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId, generate_output_document_id
from output.output_request import OutputRequest
from output.output_type import OutputType


class AuditReportJsonGenerator:

    def __init__(
        self,
        audit_query: AuditQueryService,
        audit_verifier: AuditVerifier,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(audit_query, AuditQueryService),
            "audit_query must be AuditQueryService",
        )
        require(
            isinstance(audit_verifier, AuditVerifier),
            "audit_verifier must be AuditVerifier",
        )
        require(isinstance(base_output_dir, Path), "base_output_dir must be Path")
        self._audit_query = audit_query
        self._audit_verifier = audit_verifier
        self._base_output_dir = base_output_dir

    def generate(self, request: OutputRequest) -> OutputDocument:
        require(isinstance(request, OutputRequest), "request must be OutputRequest")

        chain: AuditChain = self._audit_query.get_chain(
            subject_id=request.subject_id,
        )
        result: VerificationResult = self._audit_verifier.verify(chain)

        output_document_id = generate_output_document_id()
        file_path = self._resolve_path(request.subject_id, output_document_id)

        report: dict[str, Any] = {
            "metadata": self._build_metadata(request.subject_id, chain, result),
            "entries": self._build_entries(chain),
            "integrity": self._build_integrity(result),
            "summary": self._build_summary(result),
        }

        ensure_directory(file_path.parent)
        write_atomic_text(file_path, json.dumps(report, indent=2, default=str))

        return OutputDocument(
            output_document_id=output_document_id,
            subject_id=request.subject_id,
            output_type=OutputType.AUDIT_REPORT,
            output_format=OutputFormat.JSON,
            generated_at=result.verified_at,
            file_path=file_path,
        )

    def _build_metadata(
        self,
        subject_id: EntityId,
        chain: AuditChain,
        result: VerificationResult,
    ) -> dict[str, Any]:
        return {
            "subject_id": str(subject_id),
            "chain_length": len(chain.entries),
            "generated_at": result.verified_at.isoformat(),
        }

    def _build_entries(self, chain: AuditChain) -> list[dict[str, Any]]:
        return [
            {
                "audit_id": str(entry.audit_id),
                "event_type": entry.event_type.value,
                "actor_id": str(entry.actor_id),
                "subject_id": str(entry.subject_id),
                "occurred_at": entry.occurred_at.isoformat(),
                "payload": entry.payload,
                "previous_hash": entry.previous_hash,
            }
            for entry in chain.entries
        ]

    def _build_integrity(
        self,
        result: VerificationResult,
    ) -> dict[str, Any]:
        return {
            "passed": result.integrity_result.is_valid,
            "violations": [
                self._serialize_violation(v) for v in result.integrity_result.violations
            ],
        }

    def _build_summary(
        self,
        result: VerificationResult,
    ) -> dict[str, Any]:
        return {
            "chain_length": result.chain_length,
            "verified_entries": result.verified_entries,
            "failed_entries": result.chain_length - result.verified_entries,
            "verified_at": result.verified_at.isoformat(),
        }

    @staticmethod
    def _serialize_violation(v: IntegrityViolation) -> dict[str, Any]:
        return {
            "kind": v.kind.value,
            "index": v.index,
            "detail": v.detail,
        }

    def _resolve_path(
        self,
        subject_id: EntityId,
        output_document_id: OutputDocumentId,
    ) -> Path:
        return (
            self._base_output_dir
            / str(subject_id)
            / "audit_report"
            / f"audit_report_{output_document_id}.json"
        )
