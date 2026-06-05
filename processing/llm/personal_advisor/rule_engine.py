from __future__ import annotations

from processing.llm.personal_advisor.advice_category import AdviceCategory
from processing.llm.personal_advisor.advice_item import AdviceItem
from processing.llm.personal_advisor.context_builder import UserContext

_T = dict[str, dict[str, str]]

_TITLES: _T = {
    "doc_expiring": {
        "en": "Document Expiring Soon",
        "de": "Dokument läuft bald ab",
        "ar": "وثيقة قاربت على الانتهاء",
    },
    "doc_expired": {
        "en": "Document Expired",
        "de": "Dokument abgelaufen",
        "ar": "وثيقة منتهية الصلاحية",
    },
    "missing_fields": {
        "en": "Incomplete Profile",
        "de": "Unvollständiges Profil",
        "ar": "ملف شخصي غير مكتمل",
    },
    "open_conflicts": {
        "en": "Data Conflicts Detected",
        "de": "Datenkonflikte erkannt",
        "ar": "تعارضات في البيانات",
    },
    "health_checkup": {
        "en": "Health Check-up Reminder",
        "de": "Erinnerung an Vorsorgeuntersuchung",
        "ar": "تذكير بالفحص الصحي الدوري",
    },
    "financial_iban": {
        "en": "Banking Information Present",
        "de": "Bankdaten vorhanden",
        "ar": "بيانات مصرفية متوفرة",
    },
    "family_spouse": {
        "en": "Spouse Data May Be Needed",
        "de": "Ehepartnerdaten möglicherweise erforderlich",
        "ar": "قد تكون بيانات الزوج/ة مطلوبة",
    },
    "employment_update": {
        "en": "Employment Record Check",
        "de": "Beschäftigungsdaten prüfen",
        "ar": "مراجعة بيانات التوظيف",
    },
}

_BODIES: _T = {
    "doc_expiring": {
        "en": "'{field}' expires in {days} day(s) on {expiry}.",
        "de": "'{field}' läuft in {days} Tag(en) am {expiry} ab.",
        "ar": "'{field}' تنتهي خلال {days} يوم بتاريخ {expiry}.",
    },
    "doc_expired": {
        "en": "'{field}' expired {days} day(s) ago on {expiry}.",
        "de": "'{field}' ist seit {days} Tag(en) am {expiry} abgelaufen.",
        "ar": "'{field}' انتهت صلاحيتها منذ {days} يوم بتاريخ {expiry}.",
    },
    "missing_fields": {
        "en": "{count} required field(s) are missing from this profile.",
        "de": "{count} erforderliche Felder fehlen in diesem Profil.",
        "ar": "يوجد {count} حقل/حقول مطلوبة مفقودة في هذا الملف.",
    },
    "open_conflicts": {
        "en": "{count} unresolved data conflict(s) require attention.",
        "de": "{count} ungelöste Datenkonflikte erfordern Aufmerksamkeit.",
        "ar": "يوجد {count} تعارض/تعارضات غير محلولة تحتاج إلى انتباه.",
    },
    "health_checkup": {
        "en": "Based on age {age}, a periodic health check-up is recommended.",
        "de": "Basierend auf dem Alter {age} wird eine Vorsorgeuntersuchung empfohlen.",
        "ar": "بناءً على العمر {age}، يُنصح بإجراء فحص صحي دوري.",
    },
    "financial_iban": {
        "en": "IBAN is registered with {bank}. Ensure account details are current.",
        "de": "IBAN ist bei {bank} registriert. Stellen Sie sicher, dass die Kontodaten aktuell sind.",
        "ar": "الـ IBAN مسجّل لدى {bank}. تأكد من أن بيانات الحساب محدّثة.",
    },
    "family_spouse": {
        "en": "Marital status is '{status}'. Spouse or dependent records may be required.",
        "de": "Familienstand ist '{status}'. Daten des Ehepartners oder Angehörigen können erforderlich sein.",
        "ar": "الحالة الاجتماعية '{status}'. قد تكون بيانات الزوج/ة أو المعالين مطلوبة.",
    },
    "employment_update": {
        "en": "Employed at '{employer}' as '{job}'. Verify social insurance records are up to date.",
        "de": "Beschäftigt bei '{employer}' als '{job}'. Sozialversicherungsdaten auf Aktualität prüfen.",
        "ar": "يعمل لدى '{employer}' بمسمى '{job}'. تحقق من تحديث سجلات التأمين الاجتماعي.",
    },
}

_SUGGESTIONS: _T = {
    "doc_expiring": {
        "en": "Initiate renewal process for '{field}' before {expiry}.",
        "de": "Verlängerungsprozess für '{field}' vor dem {expiry} einleiten.",
        "ar": "ابدأ إجراءات تجديد '{field}' قبل {expiry}.",
    },
    "doc_expired": {
        "en": "Renew '{field}' immediately — it has already expired.",
        "de": "'{field}' sofort erneuern — es ist bereits abgelaufen.",
        "ar": "جدّد '{field}' فوراً — لقد انتهت صلاحيتها.",
    },
    "missing_fields": {
        "en": "Complete the missing fields to improve profile accuracy.",
        "de": "Fehlende Felder ausfüllen, um die Profilgenauigkeit zu verbessern.",
        "ar": "أكمل الحقول المفقودة لتحسين دقة الملف الشخصي.",
    },
    "open_conflicts": {
        "en": "Review and resolve all open data conflicts.",
        "de": "Alle offenen Datenkonflikte überprüfen und lösen.",
        "ar": "راجع وحلّ جميع تعارضات البيانات المفتوحة.",
    },
    "health_checkup": {
        "en": "Schedule a health check-up with your doctor.",
        "de": "Einen Vorsorge-Termin beim Arzt vereinbaren.",
        "ar": "احجز موعداً للفحص الصحي مع طبيبك.",
    },
    "financial_iban": {
        "en": "Confirm your bank account details are still valid.",
        "de": "Bestätigen Sie, dass Ihre Bankdaten noch gültig sind.",
        "ar": "تأكد من أن بيانات حسابك المصرفي لا تزال سارية.",
    },
    "family_spouse": {
        "en": "Consider adding spouse or dependent records to the system.",
        "de": "Erwägen Sie, die Daten des Ehepartners oder Angehörigen hinzuzufügen.",
        "ar": "فكّر في إضافة بيانات الزوج/ة أو المعالين إلى النظام.",
    },
    "employment_update": {
        "en": "Verify that your Sozialversicherung and tax records reflect your current role.",
        "de": "Stellen Sie sicher, dass Sozialversicherung und Steuerdaten Ihre aktuelle Stelle widerspiegeln.",
        "ar": "تحقق من أن سجلات التأمين الاجتماعي والضرائب تعكس وظيفتك الحالية.",
    },
}


def _t(table: _T, key: str, locale: str, **kwargs: object) -> str:
    return table[key].get(locale, table[key]["en"]).format(**kwargs)


def run_rules(ctx: UserContext, locale: str) -> list[AdviceItem]:
    items: list[AdviceItem] = []
    eid = ctx.entity_id

    for doc in ctx.expiring_docs:
        days: int = doc["days"]
        expired = days < 0
        rule_key = "doc_expired" if expired else "doc_expiring"
        sev = "critical" if abs(days) <= 30 or expired else "warning"

        items.append(
            AdviceItem(
                category=AdviceCategory.DOCUMENTS,
                severity=sev,
                title=_t(_TITLES, rule_key, locale),
                body=_t(
                    _BODIES,
                    rule_key,
                    locale,
                    field=doc["field"],
                    days=abs(days),
                    expiry=doc["expiry"],
                ),
                suggestion=_t(
                    _SUGGESTIONS,
                    rule_key,
                    locale,
                    field=doc["field"],
                    expiry=doc["expiry"],
                ),
                entity_id=eid,
                locale=locale,
            )
        )

    if len(ctx.missing_fields) > 0:
        items.append(
            AdviceItem(
                category=AdviceCategory.GENERAL,
                severity="warning",
                title=_t(_TITLES, "missing_fields", locale),
                body=_t(
                    _BODIES, "missing_fields", locale, count=len(ctx.missing_fields)
                ),
                suggestion=_t(_SUGGESTIONS, "missing_fields", locale),
                entity_id=eid,
                locale=locale,
            )
        )

    if ctx.open_conflicts > 0:
        items.append(
            AdviceItem(
                category=AdviceCategory.CONFLICTS,
                severity="critical",
                title=_t(_TITLES, "open_conflicts", locale),
                body=_t(_BODIES, "open_conflicts", locale, count=ctx.open_conflicts),
                suggestion=_t(_SUGGESTIONS, "open_conflicts", locale),
                entity_id=eid,
                locale=locale,
            )
        )

    if ctx.age is not None and ctx.age >= 35:
        items.append(
            AdviceItem(
                category=AdviceCategory.HEALTH,
                severity="info",
                title=_t(_TITLES, "health_checkup", locale),
                body=_t(_BODIES, "health_checkup", locale, age=ctx.age),
                suggestion=_t(_SUGGESTIONS, "health_checkup", locale),
                entity_id=eid,
                locale=locale,
            )
        )

    if ctx.has_iban and ctx.bank_name:
        items.append(
            AdviceItem(
                category=AdviceCategory.FINANCIAL,
                severity="info",
                title=_t(_TITLES, "financial_iban", locale),
                body=_t(_BODIES, "financial_iban", locale, bank=ctx.bank_name),
                suggestion=_t(_SUGGESTIONS, "financial_iban", locale),
                entity_id=eid,
                locale=locale,
            )
        )

    if ctx.marital_status and ctx.marital_status.lower() in (
        "married",
        "verheiratet",
        "متزوج",
        "متزوجة",
    ):
        items.append(
            AdviceItem(
                category=AdviceCategory.FAMILY,
                severity="info",
                title=_t(_TITLES, "family_spouse", locale),
                body=_t(_BODIES, "family_spouse", locale, status=ctx.marital_status),
                suggestion=_t(_SUGGESTIONS, "family_spouse", locale),
                entity_id=eid,
                locale=locale,
            )
        )

    if ctx.employer and ctx.job_title:
        items.append(
            AdviceItem(
                category=AdviceCategory.EMPLOYMENT,
                severity="info",
                title=_t(_TITLES, "employment_update", locale),
                body=_t(
                    _BODIES,
                    "employment_update",
                    locale,
                    employer=ctx.employer,
                    job=ctx.job_title,
                ),
                suggestion=_t(_SUGGESTIONS, "employment_update", locale),
                entity_id=eid,
                locale=locale,
            )
        )

    return items
