from __future__ import annotations

from processing.llm.llm_factory import (
    make_advisory_llm,
    make_fast_llm,
    make_null_llm,
    make_quality_llm,
)
from processing.llm.llm_port import LLMPort
from processing.llm.personal_advisor.personal_advisor import PersonalAdvisor
from processing.llm.proactive_advisor import ProactiveAdvisor


def make_proactive_advisor(
    locale: str = "en",
    fast: bool = True,
    llm: LLMPort | None = None,
) -> ProactiveAdvisor:
    resolved_llm = llm or (make_fast_llm() if fast else make_quality_llm())
    return ProactiveAdvisor(llm=resolved_llm, locale=locale)


def make_personal_advisor(
    locale: str = "en",
    fast: bool = True,
    llm: LLMPort | None = None,
) -> PersonalAdvisor:
    resolved_llm = llm or (make_fast_llm() if fast else make_quality_llm())
    return PersonalAdvisor(llm=resolved_llm, locale=locale)


def make_grounded_advisory_llm() -> LLMPort:
    return make_advisory_llm()


def make_null_advisors(
    locale: str = "en",
) -> tuple[ProactiveAdvisor, PersonalAdvisor]:
    llm = make_null_llm()
    return (
        ProactiveAdvisor(llm=llm, locale=locale),
        PersonalAdvisor(llm=llm, locale=locale),
    )
