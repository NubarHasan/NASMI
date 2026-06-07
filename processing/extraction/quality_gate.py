from __future__ import annotations

import re

from dataclasses import replace

from processing.extraction.candidate_fact import CandidateFact

_LABEL_VALUES: frozenset[str] = frozenset(
    {
        "name",
        "surname",
        "family name",
        "given name",
        "given names",
        "vornamen",
        "vorname",
        "geburtsname",
        "nationality",
        "nationalité",
        "nationalite",
        "staatsangehörigkeit",
        "staatsangehoerigkeit",
        "date of birth",
        "birth date",
        "geburt",
        "geburtsdatum",
        "place of birth",
        "geburtsort",
        "sex",
        "gender",
        "geschlecht",
        "sexe",
        "height",
        "größe",
        "groesse",
        "eye color",
        "eye colour",
        "colour of eyes",
        "augenfarbe",
        "address",
        "residence",
        "wohnort",
        "domicile",
        "passport",
        "passport no",
        "passport number",
        "document no",
        "document number",
        "issuing authority",
        "authority",
        "autorité",
        "autorite",
        "ausstellende behörde",
        "ausstellungsbehörde",
        "iban",
        "bic",
        "swift",
        "tax id",
        "steuer id",
        "employer",
        "arbeitgeber",
        "employee",
        "arbeitnehmer",
        "gross salary",
        "net salary",
        "invoice number",
        "invoice no",
        "customer number",
        "inhabers",
        "republic",
        "federale",
        "federal republic of germany",
        "bundesrepublik deutschland",
        "republique federale",
        "république fédérale",
        "passeport",
        "reisepass",
        "gsnummer",
    }
)

_COUNTRY_NOISE: frozenset[str] = frozenset(
    {
        "deutschland",
        "germany",
        "allemagne",
        "republic",
        "federal",
        "federale",
        "deutsch",
        "german",
    }
)

_DATE_FIELDS: frozenset[str] = frozenset(
    {
        "date",
        "date_of_birth",
        "date_of_issue",
        "date_of_expiry",
        "expiry_date",
        "issue_date",
    }
)

_TEXT_FIELDS: frozenset[str] = frozenset(
    {
        "surname",
        "given_names",
        "place_of_birth",
        "issuing_authority",
        "address",
        "employer",
        "employee",
        "nationality",
    }
)

_FINANCIAL_FIELDS: frozenset[str] = frozenset(
    {
        "amount",
        "gross_salary",
        "net_salary",
    }
)

_ALLOWED_GENERIC_TYPES: frozenset[str] = frozenset(
    {
        "email",
        "phone_number",
        "date",
        "amount",
        "document_number",
        "mrz_line",
        "iban",
        "bic",
        "passport_number",
        "tax_id",
        "invoice_number",
        "customer_number",
    }
)


def filter_candidate_facts(facts: list[CandidateFact]) -> list[CandidateFact]:
    result: list[CandidateFact] = []
    seen: set[tuple[str, str]] = set()

    for fact in facts:
        normalized = normalize_value(fact.fact_type, fact.normalized_value or fact.raw_value)
        raw = normalize_display_value(fact.raw_value or normalized)

        checked = replace(
            fact,
            raw_value=raw,
            normalized_value=normalized,
            metadata={
                **dict(fact.metadata or {}),
                "quality_gate": "passed",
            },
        )

        if not is_valid_candidate_fact(checked):
            continue

        key = (
            str(checked.fact_type).strip().lower(),
            str(checked.normalized_value).strip().lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(checked)

    return result


def is_valid_candidate_fact(fact: CandidateFact) -> bool:
    field = normalize_key(fact.fact_type)
    value = fact.normalized_value or fact.raw_value
    value_norm = normalize_text(value)

    if not field or not value_norm:
        return False

    if field in {"document_label", "review_candidate"}:
        return False

    if is_label_as_value(field, value):
        return False

    if is_ocr_junk(value):
        return False

    if field in _DATE_FIELDS:
        return is_date_value(value)

    if field == "sex":
        return value_norm in {
            "m",
            "f",
            "x",
            "male",
            "female",
            "männlich",
            "maennlich",
            "weiblich",
            "masculin",
            "féminin",
            "feminin",
        }

    if field == "height":
        return bool(re.fullmatch(r"\d{2,3}\s?(cm|m)?", value_norm))

    if field == "eye_color":
        return value_norm in {
            "brown",
            "blue",
            "green",
            "grey",
            "gray",
            "black",
            "braun",
            "blau",
            "gruen",
            "grün",
            "grau",
            "schwarz",
            "marron",
            "bleu",
            "vert",
            "gris",
            "noir",
        }

    if field == "passport_number":
        return bool(re.fullmatch(r"[A-Z0-9]{6,12}", value.upper())) and bool(re.search(r"\d", value))

    if field == "document_number":
        return bool(re.fullmatch(r"[A-Z]{1,3}\d{5,10}", value.upper()))

    if field == "iban":
        return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", value.upper().replace(" ", "")))

    if field == "bic":
        return bool(re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", value.upper().replace(" ", ""))) and value_norm not in _COUNTRY_NOISE

    if field == "email":
        return bool(re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", value, re.IGNORECASE))

    if field == "phone_number":
        digits = re.sub(r"\D", "", value)
        return 8 <= len(digits) <= 16

    if field in _FINANCIAL_FIELDS:
        return bool(re.search(r"\d", value)) and bool(re.search(r"(eur|€)", value_norm))

    if field in {"invoice_number", "customer_number", "tax_id"}:
        return bool(re.search(r"\d", value)) and len(value_norm) >= 4

    if field in _TEXT_FIELDS:
        return is_human_text_value(value)

    if field in _ALLOWED_GENERIC_TYPES:
        return len(value_norm) >= 2

    return len(value_norm) >= 2 and not is_label_as_value(field, value)


def is_label_as_value(field: str, value: str) -> bool:
    field_norm = normalize_key(field)
    value_norm = normalize_text(value)

    if not value_norm:
        return True

    if value_norm == field_norm:
        return True

    if value_norm in _LABEL_VALUES:
        return True

    aliases = {
        "surname": {"name", "surname", "family name", "geburtsname", "nom"},
        "given_names": {"given name", "given names", "vornamen", "vorname"},
        "date_of_birth": {"date of birth", "birth date", "geburt", "geburtsdatum"},
        "nationality": {"nationality", "nationalité", "nationalite", "staatsangehörigkeit", "staatsangehoerigkeit"},
        "sex": {"sex", "gender", "geschlecht", "sexe"},
        "height": {"height", "größe", "groesse", "taille"},
        "eye_color": {"eye color", "eye colour", "colour of eyes", "augenfarbe"},
        "address": {"address", "residence", "wohnort", "domicile", "adresse", "anschrift"},
        "passport_number": {"passport no", "passport number", "passport", "document no", "document number"},
        "issuing_authority": {"authority", "issuing authority", "autorité", "autorite", "ausstellende behörde", "ausstellungsbehörde"},
        "iban": {"iban"},
        "bic": {"bic", "swift"},
    }

    if value_norm in aliases.get(field_norm, set()):
        return True

    hits = 0
    for label in _LABEL_VALUES:
        if re.search(rf"(^|\b){re.escape(label)}(\b|$)", value_norm):
            hits += 1

    return hits >= 2


def is_ocr_junk(value: str) -> bool:
    value_norm = normalize_text(value)

    if len(value_norm) <= 1:
        return True

    if any(char in value for char in "©[]{}"):
        return True

    if "<<" in value and not is_mrz_value(value):
        return True

    fake_ocr = {
        "deytschland",
        "dfutschland",
        "pfutrehland",
        "beutechland",
        "ofuteche",
        "ofatecheand",
        "nemtechi",
        "deutsenl",
        "deutecmi",
        "deuteent",
        "deutacheand",
        "deutecul",
        "ceutschl",
        "gsnummer",
    }

    if value_norm in fake_ocr:
        return True

    letters = re.sub(r"[^a-zA-Z]", "", value)
    if len(letters) >= 7:
        vowels = len(re.findall(r"[aeiouAEIOU]", letters))
        if vowels == 0:
            return True

    return False


def is_date_value(value: str) -> bool:
    return bool(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", value))


def is_mrz_value(value: str) -> bool:
    compact = value.replace(" ", "").strip().upper()
    if len(compact) < 25 or len(compact) > 44:
        return False
    if "<" not in compact:
        return False
    return bool(re.fullmatch(r"[A-Z0-9<]{25,44}", compact))


def is_human_text_value(value: str) -> bool:
    value_norm = normalize_text(value)

    if len(value_norm) < 2:
        return False

    if any(char.isdigit() for char in value_norm):
        return False

    if value_norm in _LABEL_VALUES:
        return False

    if value_norm in _COUNTRY_NOISE:
        return False

    if len(value_norm.split()) > 8:
        return False

    letters = re.sub(r"[^a-zA-ZÀ-ÿ ]", "", value)
    return len(letters.strip()) >= 2


def normalize_key(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("-", "_").replace(" ", "_")
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def normalize_text(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    value = re.sub(r"[_\-:;,.()\[\]{}©]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_display_value(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or ""))
    value = value.strip(" \t:;,.|")
    return value.strip()


def normalize_value(field: str, value: str) -> str:
    field_norm = normalize_key(field)
    value = normalize_display_value(value)

    if field_norm in {"iban", "bic", "passport_number", "document_number", "mrz_line"}:
        return value.upper().replace(" ", "")

    return value

_EXTRA_LABEL_VALUES = {
    "prenoms",
    "prénoms",
    "religious name",
    "religious name or pseudonym",
    "pseudonym",
    "residence do",
    "residence",
    "do",
}

def is_label_as_value(field: str, value: str) -> bool:
    field_norm = normalize_key(field)
    value_norm = normalize_text(value)

    if not value_norm:
        return True

    if value_norm == field_norm:
        return True

    if value_norm in _LABEL_VALUES or value_norm in _EXTRA_LABEL_VALUES:
        return True

    if "religious name" in value_norm:
        return True

    if "pseudonym" in value_norm:
        return True

    if "prenoms" in value_norm or "prénoms" in value_norm:
        return True

    if value_norm.startswith("residence"):
        return True

    aliases = {
        "surname": {"name", "surname", "family name", "geburtsname", "nom", "religious name", "religious name or pseudonym", "pseudonym"},
        "given_names": {"given name", "given names", "vornamen", "vorname", "prenoms", "prénoms"},
        "date_of_birth": {"date of birth", "birth date", "geburt", "geburtsdatum"},
        "nationality": {"nationality", "nationalité", "nationalite", "staatsangehörigkeit", "staatsangehoerigkeit"},
        "sex": {"sex", "gender", "geschlecht", "sexe"},
        "height": {"height", "größe", "groesse", "taille"},
        "eye_color": {"eye color", "eye colour", "colour of eyes", "augenfarbe"},
        "address": {"address", "residence", "wohnort", "domicile", "adresse", "anschrift"},
        "passport_number": {"passport no", "passport number", "passport", "document no", "document number"},
        "issuing_authority": {"authority", "issuing authority", "autorité", "autorite", "ausstellende behörde", "ausstellungsbehörde"},
        "iban": {"iban"},
        "bic": {"bic", "swift"},
    }

    if value_norm in aliases.get(field_norm, set()):
        return True

    hits = 0
    for label in list(_LABEL_VALUES) + list(_EXTRA_LABEL_VALUES):
        if re.search(rf"(^|\b){re.escape(label)}(\b|$)", value_norm):
            hits += 1

    return hits >= 1 and field_norm in {"surname", "given_names", "address", "nationality", "date_of_birth"}


def is_human_text_value(value: str) -> bool:
    value_norm = normalize_text(value)

    if len(value_norm) < 2:
        return False

    if is_label_as_value("", value):
        return False

    if any(char.isdigit() for char in value_norm):
        return False

    if any(char in value for char in "/\\|<>[]{}©"):
        return False

    if value_norm in _LABEL_VALUES:
        return False

    if value_norm in _COUNTRY_NOISE:
        return False

    if len(value_norm.split()) > 5:
        return False

    letters = re.sub(r"[^a-zA-ZÀ-ÿ ]", "", value)
    return len(letters.strip()) >= 2


def is_valid_candidate_fact(fact: CandidateFact) -> bool:
    field = normalize_key(fact.fact_type)
    value = fact.normalized_value or fact.raw_value
    value_norm = normalize_text(value)

    if not field or not value_norm:
        return False

    if field in {"document_label", "review_candidate"}:
        return False

    if is_label_as_value(field, value):
        return False

    if is_ocr_junk(value):
        return False

    if field == "phone_number":
        if is_date_value(value):
            return False
        digits = re.sub(r"\D", "", value)
        return 8 <= len(digits) <= 16 and not re.fullmatch(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", value)

    if field in _DATE_FIELDS:
        return is_date_value(value)

    if field == "sex":
        return value_norm in {"m", "f", "x", "male", "female", "männlich", "maennlich", "weiblich", "masculin", "féminin", "feminin"}

    if field == "height":
        return bool(re.fullmatch(r"\d{2,3}\s?(cm|m)?", value_norm))

    if field == "eye_color":
        return value_norm in {"brown", "blue", "green", "grey", "gray", "black", "braun", "blau", "gruen", "grün", "grau", "schwarz", "marron", "bleu", "vert", "gris", "noir"}

    if field == "passport_number":
        return bool(re.fullmatch(r"[A-Z0-9]{6,12}", value.upper())) and bool(re.search(r"\d", value))

    if field == "document_number":
        return bool(re.fullmatch(r"[A-Z]{1,3}\d{5,10}", value.upper()))

    if field == "iban":
        return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", value.upper().replace(" ", "")))

    if field == "bic":
        return bool(re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", value.upper().replace(" ", ""))) and value_norm not in _COUNTRY_NOISE

    if field == "email":
        return bool(re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", value, re.IGNORECASE))

    if field in _FINANCIAL_FIELDS:
        return bool(re.search(r"\d", value)) and bool(re.search(r"(eur|€)", value_norm))

    if field in {"invoice_number", "customer_number", "tax_id"}:
        return bool(re.search(r"\d", value)) and len(value_norm) >= 4

    if field in _TEXT_FIELDS:
        return is_human_text_value(value)

    if field == "mrz_line":
        return is_mrz_value(value)

    if field in _ALLOWED_GENERIC_TYPES:
        return len(value_norm) >= 2

    return len(value_norm) >= 2 and not is_label_as_value(field, value)

_EXTRA_BAD_VALUES_2 = {
    "telefon",
    "phone",
    "telephone",
    "tel",
    "strabe",
    "strasse",
    "straße",
    "street",
    "geburtsland",
    "birth country",
    "country of birth",
    "land",
}

def is_label_as_value(field: str, value: str) -> bool:
    field_norm = normalize_key(field)
    value_norm = normalize_text(value)

    if not value_norm:
        return True

    if value_norm == field_norm:
        return True

    if value_norm in _LABEL_VALUES or value_norm in _EXTRA_LABEL_VALUES or value_norm in _EXTRA_BAD_VALUES_2:
        return True

    if "religious name" in value_norm:
        return True

    if "pseudonym" in value_norm:
        return True

    if "prenoms" in value_norm or "prénoms" in value_norm:
        return True

    if value_norm.startswith("residence"):
        return True

    if value_norm in {"telefon", "strabe", "strasse", "straße", "geburtsland"}:
        return True

    aliases = {
        "surname": {"name", "surname", "family name", "geburtsname", "nom", "religious name", "religious name or pseudonym", "pseudonym", "telefon"},
        "given_names": {"given name", "given names", "vornamen", "vorname", "prenoms", "prénoms"},
        "date_of_birth": {"date of birth", "birth date", "geburt", "geburtsdatum"},
        "place_of_birth": {"place of birth", "geburtsort", "geburtsland", "birth country", "country of birth"},
        "nationality": {"nationality", "nationalité", "nationalite", "staatsangehörigkeit", "staatsangehoerigkeit"},
        "sex": {"sex", "gender", "geschlecht", "sexe"},
        "height": {"height", "größe", "groesse", "taille"},
        "eye_color": {"eye color", "eye colour", "colour of eyes", "augenfarbe"},
        "address": {"address", "residence", "wohnort", "domicile", "adresse", "anschrift", "straße", "strasse", "strabe", "street"},
        "passport_number": {"passport no", "passport number", "passport", "document no", "document number"},
        "issuing_authority": {"authority", "issuing authority", "autorité", "autorite", "ausstellende behörde", "ausstellungsbehörde"},
        "phone_number": {"telefon", "phone", "telephone", "tel"},
        "iban": {"iban"},
        "bic": {"bic", "swift"},
    }

    if value_norm in aliases.get(field_norm, set()):
        return True

    hits = 0
    for label in list(_LABEL_VALUES) + list(_EXTRA_LABEL_VALUES) + list(_EXTRA_BAD_VALUES_2):
        if re.search(rf"(^|\b){re.escape(label)}(\b|$)", value_norm):
            hits += 1

    return hits >= 1 and field_norm in {"surname", "given_names", "address", "nationality", "date_of_birth", "place_of_birth", "phone_number"}


def is_valid_phone_number(value: str) -> bool:
    value_clean = value.strip()

    if is_date_value(value_clean):
        return False

    if re.search(r"\d+[.]\d+", value_clean):
        return False

    if not re.search(r"(^|\s|\()(\+|00)\d", value_clean):
        return False

    digits = re.sub(r"\D", "", value_clean)

    if len(digits) < 9 or len(digits) > 16:
        return False

    if len(set(digits)) <= 2:
        return False

    return True


def is_human_text_value(value: str) -> bool:
    value_norm = normalize_text(value)

    if len(value_norm) < 2:
        return False

    if is_label_as_value("", value):
        return False

    if any(char.isdigit() for char in value_norm):
        return False

    if any(char in value for char in "/\\|<>[]{}©"):
        return False

    if value_norm in _LABEL_VALUES or value_norm in _EXTRA_BAD_VALUES_2:
        return False

    if value_norm in _COUNTRY_NOISE:
        return False

    if len(value_norm.split()) > 5:
        return False

    letters = re.sub(r"[^a-zA-ZÀ-ÿ ]", "", value)
    return len(letters.strip()) >= 2


def is_valid_candidate_fact(fact: CandidateFact) -> bool:
    field = normalize_key(fact.fact_type)
    value = fact.normalized_value or fact.raw_value
    value_norm = normalize_text(value)

    if not field or not value_norm:
        return False

    if field in {"document_label", "review_candidate"}:
        return False

    if is_label_as_value(field, value):
        return False

    if is_ocr_junk(value):
        return False

    if field == "phone_number":
        return is_valid_phone_number(value)

    if field in _DATE_FIELDS:
        return is_date_value(value)

    if field == "sex":
        return value_norm in {"m", "f", "x", "male", "female", "männlich", "maennlich", "weiblich", "masculin", "féminin", "feminin"}

    if field == "height":
        return bool(re.fullmatch(r"\d{2,3}\s?(cm|m)?", value_norm))

    if field == "eye_color":
        return value_norm in {"brown", "blue", "green", "grey", "gray", "black", "braun", "blau", "gruen", "grün", "grau", "schwarz", "marron", "bleu", "vert", "gris", "noir"}

    if field == "passport_number":
        return bool(re.fullmatch(r"[A-Z0-9]{6,12}", value.upper())) and bool(re.search(r"\d", value))

    if field == "document_number":
        return bool(re.fullmatch(r"[A-Z]{1,3}\d{5,10}", value.upper()))

    if field == "iban":
        return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", value.upper().replace(" ", "")))

    if field == "bic":
        return bool(re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", value.upper().replace(" ", ""))) and value_norm not in _COUNTRY_NOISE

    if field == "email":
        return bool(re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", value, re.IGNORECASE))

    if field in _FINANCIAL_FIELDS:
        return bool(re.search(r"\d", value)) and bool(re.search(r"(eur|€)", value_norm))

    if field in {"invoice_number", "customer_number", "tax_id"}:
        return bool(re.search(r"\d", value)) and len(value_norm) >= 4

    if field in _TEXT_FIELDS or field == "place_of_birth":
        return is_human_text_value(value)

    if field == "mrz_line":
        return is_mrz_value(value)

    if field in _ALLOWED_GENERIC_TYPES:
        return len(value_norm) >= 2

    return len(value_norm) >= 2 and not is_label_as_value(field, value)
