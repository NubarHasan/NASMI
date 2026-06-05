from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from knowledge.knowledge_fact_type import KnowledgeFactType
from knowledge.profile import Profile
from knowledge.vault import Vault


@dataclass
class UserContext:
    entity_id: str
    display_name: str
    age: int | None
    nationality: str | None
    country: str | None
    city: str | None
    marital_status: str | None
    employer: str | None
    job_title: str | None
    has_iban: bool
    bank_name: str | None
    has_passport: bool
    has_id_card: bool
    open_conflicts: int
    missing_fields: frozenset[str]
    expiring_docs: list[dict[str, Any]] = field(default_factory=list)

    def to_prompt_block(self, locale: str = "en") -> str:
        lines: list[str] = []

        _LABELS: dict[str, dict[str, str]] = {
            "en": {
                "name": "Name",
                "age": "Age",
                "nation": "Nationality",
                "country": "Country",
                "city": "City",
                "marital": "Marital status",
                "employer": "Employer",
                "job": "Job title",
                "iban": "Has IBAN",
                "bank": "Bank",
                "passport": "Has passport",
                "id_card": "Has ID card",
                "conflicts": "Open conflicts",
                "missing": "Missing fields",
            },
            "de": {
                "name": "Name",
                "age": "Alter",
                "nation": "Staatsangehörigkeit",
                "country": "Land",
                "city": "Stadt",
                "marital": "Familienstand",
                "employer": "Arbeitgeber",
                "job": "Berufsbezeichnung",
                "iban": "Hat IBAN",
                "bank": "Bank",
                "passport": "Hat Reisepass",
                "id_card": "Hat Personalausweis",
                "conflicts": "Offene Konflikte",
                "missing": "Fehlende Felder",
            },
            "ar": {
                "name": "الاسم",
                "age": "العمر",
                "nation": "الجنسية",
                "country": "البلد",
                "city": "المدينة",
                "marital": "الحالة الاجتماعية",
                "employer": "صاحب العمل",
                "job": "المسمى الوظيفي",
                "iban": "لديه IBAN",
                "bank": "البنك",
                "passport": "لديه جواز سفر",
                "id_card": "لديه بطاقة هوية",
                "conflicts": "تعارضات مفتوحة",
                "missing": "حقول مفقودة",
            },
        }

        lbl = _LABELS.get(locale, _LABELS["en"])

        def _add(key: str, value: Any) -> None:
            if value is not None:
                lines.append(f"{lbl[key]}: {value}")

        _add("name", self.display_name)
        _add("age", self.age)
        _add("nation", self.nationality)
        _add("country", self.country)
        _add("city", self.city)
        _add("marital", self.marital_status)
        _add("employer", self.employer)
        _add("job", self.job_title)
        _add("iban", "yes" if self.has_iban else None)
        _add("bank", self.bank_name)
        _add("passport", "yes" if self.has_passport else None)
        _add("id_card", "yes" if self.has_id_card else None)

        if self.open_conflicts > 0:
            lines.append(f"{lbl['conflicts']}: {self.open_conflicts}")

        if self.missing_fields:
            lines.append(f"{lbl['missing']}: {', '.join(sorted(self.missing_fields))}")

        if self.expiring_docs:
            for doc in self.expiring_docs:
                lines.append(f"  ⚠ {doc['field']} → {doc['expiry']} ({doc['days']}d)")

        return "\n".join(lines)


def _get_field(profile: Profile, *keys: str) -> str | None:
    for key in keys:
        pf = profile.get_field(key)
        if pf is not None:
            return str(pf.display_value)
    return None


def _calc_age(dob_str: str | None) -> int | None:
    if not dob_str:
        return None
    today = datetime.now(tz=UTC).date()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            dob = datetime.strptime(dob_str, fmt).date()
            return (
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
        except ValueError:
            continue
    return None


def _parse_date_value(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _expiring_docs(profile: Profile, warning_days: int = 90) -> list[dict[str, Any]]:
    from processing.llm.advisory_result import EXPIRY_FIELD_NAMES

    today = datetime.now(tz=UTC).date()
    result: list[dict[str, Any]] = []

    for field_name, pf in profile.fields.items():
        if field_name.lower() not in {f.lower() for f in EXPIRY_FIELD_NAMES}:
            continue

        expiry: date | None = _parse_date_value(pf.value)
        if expiry is None:
            continue

        days = (expiry - today).days
        if days <= warning_days:
            result.append(
                {
                    "field": field_name,
                    "expiry": expiry.isoformat(),
                    "days": days,
                }
            )

    return sorted(result, key=lambda x: x["days"])


def build_user_context(
    entity_id: str,
    vault: Vault,
    warning_days: int = 90,
) -> UserContext | None:
    profile = vault.get_profile(entity_id)  # type: ignore[arg-type]
    if profile is None:
        return None

    from knowledge.profile_schema_registry import get_schema, has_schema

    entity = vault.get_entity(entity_id)  # type: ignore[arg-type]
    entity_type = entity.entity_type if entity else "person"

    missing: frozenset[str] = frozenset()
    if has_schema(entity_type):
        schema = get_schema(entity_type)
        missing = schema - profile.field_names()

    open_conflicts = sum(
        1
        for c in vault.conflicts.values()
        if str(c.entity_id) == entity_id and not c.is_terminal
    )

    return UserContext(
        entity_id=entity_id,
        display_name=profile.display_name,
        age=_calc_age(_get_field(profile, KnowledgeFactType.DATE_OF_BIRTH)),
        nationality=_get_field(profile, KnowledgeFactType.NATIONALITY),
        country=_get_field(profile, KnowledgeFactType.ADDRESS_COUNTRY),
        city=_get_field(profile, KnowledgeFactType.ADDRESS_CITY),
        marital_status=_get_field(profile, KnowledgeFactType.MARITAL_STATUS),
        employer=_get_field(profile, KnowledgeFactType.EMPLOYER_NAME),
        job_title=_get_field(profile, KnowledgeFactType.JOB_TITLE),
        has_iban=profile.has_field(KnowledgeFactType.IBAN),
        bank_name=_get_field(profile, KnowledgeFactType.BANK_NAME),
        has_passport=profile.has_field(KnowledgeFactType.PASSPORT_NUMBER),
        has_id_card=profile.has_field(KnowledgeFactType.IDENTITY_CARD_NUMBER),
        open_conflicts=open_conflicts,
        missing_fields=missing,
        expiring_docs=_expiring_docs(profile, warning_days),
    )
