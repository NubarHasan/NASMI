from __future__ import annotations

from typing import Protocol

from knowledge.provenance_step import ProvenanceStep

from core.types import FactId, ProvenanceId
from knowledge.provenance import Provenance


class ProvenanceRepository(Protocol):

    def save(self, provenance: Provenance) -> None: ...

    def get(self, provenance_id: ProvenanceId) -> Provenance | None: ...

    def get_by_fact(self, fact_id: FactId) -> Provenance | None: ...

    def list_steps(
        self,
        provenance_id: ProvenanceId,
    ) -> tuple[ProvenanceStep, ...]: ...

    def list_steps_by_fact(
        self,
        fact_id: FactId,
    ) -> tuple[ProvenanceStep, ...]: ...
