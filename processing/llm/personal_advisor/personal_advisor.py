from __future__ import annotations

import logging

from knowledge.vault import Vault
from processing.llm.advisory_result import SUPPORTED_LOCALES
from processing.llm.llm_port import LLMPort
from processing.llm.personal_advisor.advice_category import AdviceCategory
from processing.llm.personal_advisor.advice_item import (
    AdviceItem,
    PersonalAdvisoryResult,
)
from processing.llm.personal_advisor.context_builder import (
    UserContext,
    build_user_context,
)
from processing.llm.personal_advisor.rule_engine import run_rules

_log = logging.getLogger(__name__)

_NO_ADVICE: dict[str, str] = {
    "en": "✅ Everything looks good. No immediate action required.",
    "de": "✅ Alles sieht gut aus. Keine sofortigen Maßnahmen erforderlich.",
    "ar": "✅ كل شيء يبدو على ما يرام. لا يلزم اتخاذ أي إجراء فوري.",
}

_PROACTIVE_SYSTEM: dict[str, str] = {
    "en": (
        "You are a proactive personal advisor with full knowledge of the user's profile. "
        "Analyse the context below and provide a comprehensive, prioritised advisory "
        "covering documents, finances, health, family, employment, and any other relevant areas. "
        "Be concise, actionable, and empathetic."
    ),
    "de": (
        "Sie sind ein proaktiver persönlicher Berater mit vollständiger Kenntnis des Benutzerprofils. "
        "Analysieren Sie den folgenden Kontext und geben Sie eine umfassende, priorisierte Beratung "
        "zu Dokumenten, Finanzen, Gesundheit, Familie, Beschäftigung und anderen relevanten Bereichen. "
        "Seien Sie präzise, handlungsorientiert und einfühlsam."
    ),
    "ar": (
        "أنت مستشار شخصي استباقي لديك معرفة كاملة بملف المستخدم. "
        "حلّل السياق أدناه وقدّم استشارة شاملة ومرتّبة حسب الأولوية "
        "تغطي الوثائق والشؤون المالية والصحة والأسرة والتوظيف وأي مجالات أخرى ذات صلة. "
        "كن موجزاً وعملياً ومتعاطفاً."
    ),
}

_REACTIVE_SYSTEM: dict[str, str] = {
    "en": (
        "You are a context-aware personal advisor. "
        "The user is asking about a specific topic. "
        "Use the profile context below to give a focused, helpful, and personalised response."
    ),
    "de": (
        "Sie sind ein kontextbewusster persönlicher Berater. "
        "Der Benutzer fragt zu einem bestimmten Thema. "
        "Nutzen Sie den folgenden Profilkontext für eine fokussierte, hilfreiche und personalisierte Antwort."
    ),
    "ar": (
        "أنت مستشار شخصي واعٍ بالسياق. "
        "المستخدم يسأل عن موضوع محدد. "
        "استخدم سياق الملف الشخصي أدناه لتقديم إجابة مركّزة ومفيدة ومخصّصة."
    ),
}


def _build_proactive_prompt(ctx: UserContext, locale: str) -> str:
    system = _PROACTIVE_SYSTEM.get(locale, _PROACTIVE_SYSTEM["en"])
    profile_block = ctx.to_prompt_block(locale)

    _INSTRUCTIONS: dict[str, str] = {
        "en": (
            "Based on the profile above, provide:\n"
            "1. A brief overall summary of the user's situation.\n"
            "2. Top priority actions (critical items first).\n"
            "3. Medium-term recommendations (finances, health, family).\n"
            "4. Any proactive suggestions the user may not have considered."
        ),
        "de": (
            "Geben Sie auf Basis des obigen Profils Folgendes an:\n"
            "1. Eine kurze Gesamtübersicht der Situation des Benutzers.\n"
            "2. Prioritäre Maßnahmen (kritische zuerst).\n"
            "3. Mittelfristige Empfehlungen (Finanzen, Gesundheit, Familie).\n"
            "4. Proaktive Vorschläge, die der Benutzer möglicherweise nicht bedacht hat."
        ),
        "ar": (
            "بناءً على الملف أعلاه، قدّم:\n"
            "1. ملخصاً موجزاً شاملاً لوضع المستخدم.\n"
            "2. الإجراءات ذات الأولوية القصوى (الحرجة أولاً).\n"
            "3. التوصيات متوسطة المدى (المالية، الصحة، الأسرة).\n"
            "4. أي اقتراحات استباقية لم يفكر فيها المستخدم بعد."
        ),
    }

    instruction = _INSTRUCTIONS.get(locale, _INSTRUCTIONS["en"])
    return f"{system}\n\n{profile_block}\n\n{instruction}"


def _build_reactive_prompt(
    ctx: UserContext,
    question: str,
    locale: str,
) -> str:
    system = _REACTIVE_SYSTEM.get(locale, _REACTIVE_SYSTEM["en"])
    profile_block = ctx.to_prompt_block(locale)

    _Q_LABEL: dict[str, str] = {
        "en": "User question",
        "de": "Benutzerfrage",
        "ar": "سؤال المستخدم",
    }
    q_label = _Q_LABEL.get(locale, _Q_LABEL["en"])

    return f"{system}\n\n{profile_block}\n\n{q_label}: {question}"


class PersonalAdvisor:
    """
    Proactive + Reactive personal advisor backed by an LLM.

    Proactive  → advise(vault, entity_id)
                 Full scan: rules + LLM summary covering all life areas.

    Reactive   → ask(vault, entity_id, question)
                 Focused answer to a specific user question using profile context.
    """

    def __init__(
        self,
        llm: LLMPort,
        locale: str = "en",
        warning_days: int = 90,
    ) -> None:
        self._llm = llm
        self._locale = locale if locale in SUPPORTED_LOCALES else "en"
        self._warning_days = warning_days

    def advise(self, vault: Vault, entity_id: str) -> PersonalAdvisoryResult:
        ctx = build_user_context(entity_id, vault, self._warning_days)
        if ctx is None:
            return self._empty_result(entity_id, "unknown")

        rule_items = run_rules(ctx, self._locale)
        rule_items.sort(
            key=lambda i: (
                0 if i.severity == "critical" else 1 if i.severity == "warning" else 2
            )
        )

        prompt = _build_proactive_prompt(ctx, self._locale)
        response = self._llm.complete(
            prompt=prompt,
            context={
                "task": "proactive_personal_advisory",
                "entity_id": entity_id,
                "locale": self._locale,
            },
        )

        if response.has_error:
            _log.warning("LLM proactive advisory failed: %s", response.failure)

        return PersonalAdvisoryResult(
            entity_id=entity_id,
            display_name=ctx.display_name,
            locale=self._locale,
            items=tuple(rule_items),
            llm_summary=response.raw_text if not response.has_error else "",
            llm_failure=response.failure,
        )

    def ask(
        self,
        vault: Vault,
        entity_id: str,
        question: str,
    ) -> PersonalAdvisoryResult:
        ctx = build_user_context(entity_id, vault, self._warning_days)
        if ctx is None:
            return self._empty_result(entity_id, "unknown")

        prompt = _build_reactive_prompt(ctx, question, self._locale)
        response = self._llm.complete(
            prompt=prompt,
            context={
                "task": "reactive_personal_advisory",
                "entity_id": entity_id,
                "locale": self._locale,
                "question": question,
            },
        )

        if response.has_error:
            _log.warning("LLM reactive advisory failed: %s", response.failure)

        return PersonalAdvisoryResult(
            entity_id=entity_id,
            display_name=ctx.display_name,
            locale=self._locale,
            items=(),
            llm_summary=response.raw_text if not response.has_error else "",
            llm_failure=response.failure,
        )

    def _empty_result(
        self, entity_id: str, display_name: str
    ) -> PersonalAdvisoryResult:
        return PersonalAdvisoryResult(
            entity_id=entity_id,
            display_name=display_name,
            locale=self._locale,
            items=(),
            llm_summary=_NO_ADVICE[self._locale],
            llm_failure=None,
        )
