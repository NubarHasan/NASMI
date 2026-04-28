import re
from dataclasses import dataclass, field
from enum import Enum
from core.events import Event, EventType
from core.event_bus import bus


class FieldCategory(Enum):
    NAME = "name"
    DATE = "date"
    ADDRESS = "address"
    IBAN = "iban"
    TAX_ID = "tax_id"
    PHONE = "phone"
    EMAIL = "email"
    ID_NUMBER = "id_number"
    SOCIAL_SEC = "social_security"
    EMPLOYER = "employer"
    AMOUNT = "amount"
    UNKNOWN = "unknown"


FIELD_PATTERNS: dict[FieldCategory, list[str]] = {
    FieldCategory.IBAN: [
        r"\bDE\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{2}\b"
    ],
    FieldCategory.TAX_ID: [
        r"\b\d{2}[\s/]\d{3}[\s/]\d{5}\b",
        r"\bSteuer(?:nummer|ID)[\s:]*\d+\b",
    ],
    FieldCategory.SOCIAL_SEC: [
        r"\b\d{2}\s?\d{6}\s?[A-Z]\s?\d{3}\b",
        r"\bSozialversicherung(?:snummer)?[\s:]*\d+\b",
    ],
    FieldCategory.ID_NUMBER: [r"\b[A-Z]{1,2}\d{6,9}\b"],
    FieldCategory.PHONE: [r"\b(?:\+49|0049|0)[\s\-]?\d{2,5}[\s\-]?\d{3,8}\b"],
    FieldCategory.EMAIL: [r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"],
    FieldCategory.IBAN: [r"\bDE\d{20}\b"],
    FieldCategory.AMOUNT: [
        r"\b\d{1,3}(?:\.\d{3})*,\d{2}\s?€\b",
        r"\b€\s?\d+(?:[.,]\d+)?\b",
    ],
    FieldCategory.DATE: [
        r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ],
}

LABEL_PATTERNS: dict[FieldCategory, list[str]] = {
    FieldCategory.NAME: ["name", "vorname", "nachname", "familienname", "full name"],
    FieldCategory.ADDRESS: ["adresse", "anschrift", "wohnort", "straße", "address"],
    FieldCategory.EMPLOYER: [
        "arbeitgeber",
        "firma",
        "unternehmen",
        "employer",
        "company",
    ],
    FieldCategory.DATE: [
        "datum",
        "geburtsdatum",
        "ausstellungsdatum",
        "date",
        "gültig bis",
    ],
    FieldCategory.TAX_ID: [
        "steuernummer",
        "steuer-id",
        "tax id",
        "steueridentifikationsnummer",
    ],
    FieldCategory.SOCIAL_SEC: [
        "sozialversicherungsnummer",
        "sv-nummer",
        "rentenversicherung",
    ],
    FieldCategory.IBAN: ["iban", "kontonummer", "bankverbindung"],
    FieldCategory.PHONE: ["telefon", "tel", "handy", "phone", "mobil"],
    FieldCategory.EMAIL: ["email", "e-mail", "elektronische post"],
}


@dataclass
class DetectedField:
    label: str
    value: str
    category: FieldCategory
    page: int
    bbox: tuple | None = None
    score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "value": self.value,
            "category": self.category.value,
            "page": self.page,
            "score": self.score,
        }


@dataclass
class FormDetectionResult:
    document_id: str
    fields: list[DetectedField] = field(default_factory=list)

    @property
    def by_category(self) -> dict[str, list[DetectedField]]:
        result: dict[str, list[DetectedField]] = {}
        for f in self.fields:
            result.setdefault(f.category.value, []).append(f)
        return result


class FormDetector:

    def detect(self, document_id: str, pages: list[dict]) -> FormDetectionResult:
        result = FormDetectionResult(document_id=document_id)

        for page in pages:
            page_num = page.get("page", 0)
            text = page.get("text", "")
            detected = self._detect_from_text(text, page_num)
            result.fields.extend(detected)

        bus.publish(
            Event(
                event_type=EventType.ENTITIES_EXTRACTED,
                payload={
                    "document_id": document_id,
                    "field_count": len(result.fields),
                    "categories": list(result.by_category.keys()),
                },
                source="form_detector",
            )
        )

        return result

    def _detect_from_text(self, text: str, page: int) -> list[DetectedField]:
        fields = []
        fields += self._match_patterns(text, page)
        fields += self._match_labels(text, page)
        return self._deduplicate(fields)

    def _match_patterns(self, text: str, page: int) -> list[DetectedField]:
        fields = []
        for category, patterns in FIELD_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    fields.append(
                        DetectedField(
                            label=category.value,
                            value=match.group().strip(),
                            category=category,
                            page=page,
                            score=0.9,
                        )
                    )
        return fields

    def _match_labels(self, text: str, page: int) -> list[DetectedField]:
        fields = []
        lines = text.splitlines()

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            for category, labels in LABEL_PATTERNS.items():
                for label in labels:
                    if label in line_lower:
                        value = self._extract_value_after_label(lines, i)
                        if value:
                            fields.append(
                                DetectedField(
                                    label=label,
                                    value=value,
                                    category=category,
                                    page=page,
                                    score=0.75,
                                )
                            )
        return fields

    def _extract_value_after_label(self, lines: list[str], index: int) -> str:
        line = lines[index]

        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()

        if index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if next_line:
                return next_line

        return ""

    def _deduplicate(self, fields: list[DetectedField]) -> list[DetectedField]:
        seen = set()
        unique = []
        for f in fields:
            key = (f.category, f.value)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique
