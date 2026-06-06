from __future__ import annotations

from dataclasses import dataclass

from processing.llm.advisory_result import AdvisoryResult
from processing.llm.personal_advisor.advice_item import PersonalAdvisoryResult


@dataclass(frozen=True)
class AdvisoryCache:
    entity_id: str
    personal: PersonalAdvisoryResult | None
    proactive: AdvisoryResult | None
