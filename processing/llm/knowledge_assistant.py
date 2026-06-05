from __future__ import annotations

from typing import Any

from processing.llm.llm_port import LLMPort
from processing.llm.llm_response import LLMResponse


class KnowledgeAssistant:

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def explain_conflict(
        self,
        conflict_summary: str,
        evidence: list[dict[str, Any]],
    ) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Explain the following conflict:\n\n{conflict_summary}",
            context={"task": "explain_conflict", "evidence": evidence},
        )

    def summarise_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> LLMResponse:
        return self._llm.complete(
            prompt="Summarise the following evidence items.",
            context={"task": "summarise_evidence", "evidence": evidence},
        )

    def explain_weighting(
        self,
        fact_summary: str,
        weights: dict[str, Any],
    ) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Explain why the following fact was weighted as it was:\n\n{fact_summary}",
            context={"task": "explain_weighting", "weights": weights},
        )

    def prepare_review_note(
        self,
        conflict_summary: str,
        evidence: list[dict[str, Any]],
    ) -> LLMResponse:
        return self._llm.complete(
            prompt=f"Prepare a review note for a human reviewer:\n\n{conflict_summary}",
            context={"task": "prepare_review_note", "evidence": evidence},
        )
