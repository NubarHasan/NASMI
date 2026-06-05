from __future__ import annotations

from processing.llm.advisory_result import AdvisoryItem

_SYSTEM_PROMPTS: dict[str, str] = {
    "en": (
        "You are a proactive document advisor. "
        "Your job is to notify the user about expiring or expired documents "
        "and provide clear, actionable suggestions. "
        "Be concise, friendly, and professional."
    ),
    "de": (
        "Sie sind ein proaktiver Dokumentenberater. "
        "Ihre Aufgabe ist es, den Benutzer über ablaufende oder abgelaufene "
        "Dokumente zu informieren und klare, umsetzbare Empfehlungen zu geben. "
        "Seien Sie präzise, freundlich und professionell."
    ),
    "ar": (
        "أنت مساعد وثائق استباقي. "
        "مهمتك إخطار المستخدم بالوثائق المنتهية أو قريبة الانتهاء "
        "وتقديم اقتراحات واضحة وقابلة للتنفيذ. "
        "كن موجزاً وودوداً ومهنياً."
    ),
}

_ITEM_TEMPLATES: dict[str, str] = {
    "en": "- {display_name}: field '{field_name}' expires on {expiry_date} ({days} days remaining). Severity: {severity}.",
    "de": "- {display_name}: Feld '{field_name}' läuft am {expiry_date} ab ({days} Tage verbleibend). Schweregrad: {severity}.",
    "ar": "- {display_name}: الحقل '{field_name}' ينتهي بتاريخ {expiry_date} (متبقي {days} يوم). الأهمية: {severity}.",
}

_INSTRUCTIONS: dict[str, str] = {
    "en": (
        "Based on the above, provide:\n"
        "1. A brief overall summary.\n"
        "2. Prioritised action items for the user.\n"
        "3. Any relevant suggestions (e.g. renewal deadlines, linked documents)."
    ),
    "de": (
        "Geben Sie auf dieser Grundlage Folgendes an:\n"
        "1. Eine kurze Gesamtzusammenfassung.\n"
        "2. Priorisierte Maßnahmen für den Benutzer.\n"
        "3. Relevante Empfehlungen (z. B. Verlängerungsfristen, verknüpfte Dokumente)."
    ),
    "ar": (
        "بناءً على ما سبق، قدّم:\n"
        "1. ملخصاً موجزاً شاملاً.\n"
        "2. إجراءات مرتّبة حسب الأولوية للمستخدم.\n"
        "3. أي اقتراحات ذات صلة (مثل مواعيد التجديد، الوثائق المرتبطة)."
    ),
}


def build_advisory_prompt(
    items: tuple[AdvisoryItem, ...],
    locale: str,
) -> str:
    locale = locale if locale in _SYSTEM_PROMPTS else "en"

    system = _SYSTEM_PROMPTS[locale]
    template = _ITEM_TEMPLATES[locale]
    instruction = _INSTRUCTIONS[locale]

    lines: list[str] = [system, ""]

    if locale == "en":
        lines.append("The following documents require attention:")
    elif locale == "de":
        lines.append("Die folgenden Dokumente erfordern Aufmerksamkeit:")
    else:
        lines.append("الوثائق التالية تحتاج إلى انتباه:")

    lines.append("")

    for item in items:
        days_display = (
            str(item.days_remaining)
            if item.days_remaining >= 0
            else f"EXPIRED ({abs(item.days_remaining)})"
        )
        lines.append(
            template.format(
                display_name=item.display_name,
                field_name=item.field_name,
                expiry_date=item.expiry_date,
                days=days_display,
                severity=item.severity,
            )
        )

    lines.append("")
    lines.append(instruction)

    return "\n".join(lines)
