from __future__ import annotations

from typing import Protocol

from core.types import EvidenceId, FactId
from knowledge.fact_evidence import FactEvidence


class FactEvidenceRepository(Protocol):

    def save(self, link: FactEvidence) -> None: ...

    def exists(
        self,
        fact_id: FactId,
        evidence_id: EvidenceId,
    ) -> bool: ...

    def list_evidence_ids(
        self,
        fact_id: FactId,
    ) -> tuple[EvidenceId, ...]: ...

    def list_fact_ids(
        self,
        evidence_id: EvidenceId,
    ) -> tuple[FactId, ...]: ...
