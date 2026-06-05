from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from knowledge.vault import Vault
from processing.llm.advisory_prompt_builder import build_advisory_prompt
from processing.llm.advisory_result import (
    EXPIRY_FIELD_NAMES,
    SUPPORTED_LOCALES,
    AdvisoryItem,
    AdvisoryResult,
)
from processing.llm.llm_port import LLMPort

_log = logging.getLogger(__name__)

_CRITICAL_DAYS: int = 30
_WARNING_DAYS: int = 90

_MSG: dict[str, dict[str, str]] = {
    "expired": {
        "en": "⛔ Document expired {days} day(s) ago.",
        "de": "⛔ Dokument ist seit {days} Tag(en) abgelaufen.",
        "ar": "⛔ انتهت صلاحية الوثيقة منذ {days} يوم.",
    },
    "critical": {
        "en": "🔴 Document expires in {days} day(s) — urgent renewal required.",
        "de": "🔴 Dokument läuft in {days} Tag(en) ab — dringende Verlängerung erforderlich.",
        "ar": "🔴 تنتهي صلاحية الوثيقة خلال {days} يوم — يلزم التجديد العاجل.",
    },
    "warning": {
        "en": "🟡 Document expires in {days} day(s) — renewal recommended soon.",
        "de": "🟡 Dokument läuft in {days} Tag(en) ab — Verlängerung wird bald empfohlen.",
        "ar": "🟡 تنتهي صلاحية الوثيقة خلال {days} يوم — يُنصح بالتجديد قريباً.",
    },
    "info": {
        "en": "🟢 Document expires in {days} day(s).",
        "de": "🟢 Dokument läuft in {days} Tag(en) ab.",
        "ar": "🟢 تنتهي صلاحية الوثيقة خلال {days} يوم.",
    },
}

_SUGGESTION: dict[str, dict[str, str]] = {
    "expired": {
        "en": "Please renew '{field}' for {name} immediately.",
        "de": "Bitte '{field}' für {name} sofort erneuern.",
        "ar": "يرجى تجديد '{field}' للمستخدم {name} فوراً.",
    },
    "critical": {
        "en": "Renew '{field}' for {name} within the next {days} day(s).",
        "de": "'{field}' für {name} innerhalb der nächsten {days} Tag(e) erneuern.",
        "ar": "جدّد '{field}' للمستخدم {name} خلال {days} يوم القادمة.",
    },
    "warning": {
        "en": "Schedule renewal of '{field}' for {name} before {date}.",
        "de": "Verlängerung von '{field}' für {name} vor dem {date} einplanen.",
        "ar": "خطّط لتجديد '{field}' للمستخدم {name} قبل {date}.",
    },
    "info": {
        "en": "'{field}' for {name} is valid until {date}.",
        "de": "'{field}' für {name} ist gültig bis {date}.",
        "ar": "'{field}' للمستخدم {name} صالح حتى {date}.",
    },
}

_NO_ITEMS_SUMMARY: dict[str, str] = {
    "en": "✅ All documents are up to date. No action required.",
    "de": "✅ Alle Dokumente sind aktuell. Keine Maßnahmen erforderlich.",
    "ar": "✅ جميع الوثائق محدّثة. لا يلزم اتخاذ أي إجراء.",
}


def _today() -> date:
    return datetime.now(tz=UTC).date()


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _severity(days: int) -> str:
    if days < 0:
        return "critical"
    if days <= _CRITICAL_DAYS:
        return "critical"
    if days <= _WARNING_DAYS:
        return "warning"
    return "info"


def _make_item(
    entity_id: str,
    display_name: str,
    field_name: str,
    expiry: date,
    today: date,
    locale: str,
) -> AdvisoryItem:
    days = (expiry - today).days
    sev = _severity(days)
    key = "expired" if days < 0 else sev
    abs_days = abs(days)

    message = _MSG[key][locale].format(days=abs_days)
    suggestion = _SUGGESTION[key][locale].format(
        field=field_name,
        name=display_name,
        days=abs_days,
        date=expiry.isoformat(),
    )

    return AdvisoryItem(
        entity_id=entity_id,
        display_name=display_name,
        field_name=field_name,
        expiry_date=expiry.isoformat(),
        days_remaining=days,
        severity=sev,
        locale=locale,
        message=message,
        suggestion=suggestion,
    )


class ProactiveAdvisor:

    def __init__(
        self,
        llm: LLMPort,
        locale: str = "en",
        critical_days: int = _CRITICAL_DAYS,
        warning_days: int = _WARNING_DAYS,
    ) -> None:
        self._llm = llm
        self._locale = locale if locale in SUPPORTED_LOCALES else "en"
        self._critical_days = critical_days
        self._warning_days = warning_days

    def advise(self, vault: Vault) -> AdvisoryResult:
        today = _today()
        items: list[AdvisoryItem] = []

        for entity_id, profile in vault.profiles.items():
            display_name = profile.display_name

            for field_name, pf in profile.fields.items():
                if field_name.lower() not in {f.lower() for f in EXPIRY_FIELD_NAMES}:
                    continue

                expiry = _parse_date(pf.value)
                if expiry is None:
                    _log.debug(
                        "skipping unparseable expiry for entity=%s field=%s",
                        entity_id,
                        field_name,
                    )
                    continue

                days = (expiry - today).days
                if days > self._warning_days:
                    continue

                items.append(
                    _make_item(
                        entity_id=str(entity_id),
                        display_name=display_name,
                        field_name=field_name,
                        expiry=expiry,
                        today=today,
                        locale=self._locale,
                    )
                )

        items.sort(key=lambda i: i.days_remaining)

        return self._build_result(tuple(items))

    def _build_result(self, items: tuple[AdvisoryItem, ...]) -> AdvisoryResult:
        if not items:
            return AdvisoryResult(
                items=(),
                locale=self._locale,
                llm_summary=_NO_ITEMS_SUMMARY[self._locale],
                llm_failure=None,
            )

        prompt = build_advisory_prompt(items, self._locale)
        response = self._llm.complete(
            prompt=prompt,
            context={
                "task": "proactive_advisory",
                "locale": self._locale,
                "item_count": len(items),
            },
        )

        if response.has_error:
            _log.warning("LLM advisory failed: %s", response.failure)

        return AdvisoryResult(
            items=items,
            locale=self._locale,
            llm_summary=response.raw_text if not response.has_error else "",
            llm_failure=response.failure,
        )
