from __future__ import annotations

from processing.llm.advisory_result import SUPPORTED_LOCALES, AdvisoryResult
from processing.llm.personal_advisor.advice_item import PersonalAdvisoryResult


class AdvisoryVM:

    def refresh(
        self,
        entity_id: str,
    ) -> tuple[PersonalAdvisoryResult | None, AdvisoryResult | None]:
        """
        Returns (personal, proactive) advisory results for the given entity.
        Both may be None if no data is available.
        Stub implementation — replace with real data-source calls.
        """
        return None, None

    def get_supported_locales(self) -> frozenset[str]:
        return SUPPORTED_LOCALES
