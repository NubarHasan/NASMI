import re
import json
import spacy
from dataclasses import dataclass, field
from llm.ollama_client import OllamaClient

SYSTEM_PROMPT = """You are a precise document entity extractor.
Extract structured information from the given text and return ONLY valid JSON.
Do not add explanations or markdown formatting."""

ENTITY_PROMPT = """Extract all entities from the following document text.
Return a JSON object with these keys:
- full_name: string or null
- date_of_birth: string (YYYY-MM-DD) or null
- nationality: string or null
- id_number: string or null
- passport_number: string or null
- address: string or null
- employer: string or null
- issue_date: string (YYYY-MM-DD) or null
- expiry_date: string (YYYY-MM-DD) or null
- document_type: string or null
- extra: object with any additional fields found

Text:
{text}"""


@dataclass
class ExtractedEntities:
    full_name: str | None = None
    date_of_birth: str | None = None
    nationality: str | None = None
    id_number: str | None = None
    passport_number: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    employer: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    document_type: str | None = None
    extra: dict = field(default_factory=dict)
    confidence: float = 0.0
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth,
            "nationality": self.nationality,
            "id_number": self.id_number,
            "passport_number": self.passport_number,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "employer": self.employer,
            "issue_date": self.issue_date,
            "expiry_date": self.expiry_date,
            "document_type": self.document_type,
            "extra": self.extra,
            "confidence": self.confidence,
        }


class NEREngine:

    _nlp_de = None
    _nlp_en = None

    def __init__(self) -> None:
        self.client = OllamaClient()
        if NEREngine._nlp_de is None:
            NEREngine._nlp_de = spacy.load("de_core_news_lg")
        if NEREngine._nlp_en is None:
            NEREngine._nlp_en = spacy.load("en_core_web_lg")

    def extract(self, text: str, model: str = "text") -> ExtractedEntities:
        entities = ExtractedEntities()
        self._apply_regex(text, entities)
        self._apply_spacy(text, entities)
        entities.confidence = self._score(entities)
        if entities.confidence < 0.5:
            self._apply_ollama(text, entities, model)
            entities.confidence = self._score(entities)
        return entities

    def _apply_regex(self, text: str, e: ExtractedEntities) -> None:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            e.email = email_match.group()

        phone_match = re.search(r"(\+?\d[\d\s\-\(\)]{7,}\d)", text)
        if phone_match:
            e.phone = phone_match.group().strip()

        date_patterns = [
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{2}\.\d{2}\.\d{4})\b",
            r"\b(\d{2}/\d{2}/\d{4})\b",
        ]
        dates_found = []
        for pattern in date_patterns:
            dates_found += re.findall(pattern, text)

        if dates_found and not e.date_of_birth:
            e.date_of_birth = dates_found[0]
        if len(dates_found) > 1 and not e.issue_date:
            e.issue_date = dates_found[1]
        if len(dates_found) > 2 and not e.expiry_date:
            e.expiry_date = dates_found[2]

        id_match = re.search(r"\b([A-Z]{1,2}\d{6,9})\b", text)
        if id_match:
            e.id_number = id_match.group()

        passport_match = re.search(r"\b([A-Z]{2}\d{7})\b", text)
        if passport_match:
            e.passport_number = passport_match.group()

    def _apply_spacy(self, text: str, e: ExtractedEntities) -> None:
        for nlp in [NEREngine._nlp_de, NEREngine._nlp_en]:
            if nlp is None:
                continue
            doc = nlp(text[:3000])
            for ent in doc.ents:
                if ent.label_ == "PER" and not e.full_name:
                    e.full_name = ent.text
                elif ent.label_ in ("GPE", "LOC") and not e.address:
                    e.address = ent.text
                elif ent.label_ == "ORG" and not e.employer:
                    e.employer = ent.text
                elif ent.label_ in ("NORP", "GPE") and not e.nationality:
                    e.nationality = ent.text

    def _apply_ollama(self, text: str, e: ExtractedEntities, model: str) -> None:
        try:
            prompt = ENTITY_PROMPT.format(text=text[:2000])
            raw = self.client.generate(
                prompt,
                model=self.client.models.get(model, self.client.models["text"]),
                system=SYSTEM_PROMPT,
            )

            e.raw_response = raw
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            e.full_name = e.full_name or data.get("full_name")
            e.date_of_birth = e.date_of_birth or data.get("date_of_birth")
            e.nationality = e.nationality or data.get("nationality")
            e.id_number = e.id_number or data.get("id_number")
            e.passport_number = e.passport_number or data.get("passport_number")
            e.address = e.address or data.get("address")
            e.employer = e.employer or data.get("employer")
            e.issue_date = e.issue_date or data.get("issue_date")
            e.expiry_date = e.expiry_date or data.get("expiry_date")
            e.document_type = e.document_type or data.get("document_type")
            extra = data.get("extra", {})
            if extra:
                e.extra.update(extra)
        except Exception:
            pass

    def _score(self, e: ExtractedEntities) -> float:
        fields = [
            e.full_name,
            e.date_of_birth,
            e.nationality,
            e.id_number,
            e.passport_number,
            e.document_type,
        ]
        filled = sum(1 for f in fields if f)
        return round(filled / len(fields), 2)
