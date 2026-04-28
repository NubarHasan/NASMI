import json
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
- phone: string or null
- email: string or null
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

    def __init__(self) -> None:
        self.client = OllamaClient()

    def extract(self, text: str, model: str = "text") -> ExtractedEntities:
        prompt = ENTITY_PROMPT.format(text=text[:4000])
        raw = self.client.generate(
            prompt, model=self.client.models[model], system=SYSTEM_PROMPT
        )
        entities = self._parse(raw)
        entities.confidence = self._score(entities)
        return entities

    def _parse(self, raw: str) -> ExtractedEntities:
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            return ExtractedEntities(
                full_name=data.get("full_name"),
                date_of_birth=data.get("date_of_birth"),
                nationality=data.get("nationality"),
                id_number=data.get("id_number"),
                passport_number=data.get("passport_number"),
                address=data.get("address"),
                phone=data.get("phone"),
                email=data.get("email"),
                employer=data.get("employer"),
                issue_date=data.get("issue_date"),
                expiry_date=data.get("expiry_date"),
                document_type=data.get("document_type"),
                extra=data.get("extra", {}),
                raw_response=raw,
            )
        except Exception:
            return ExtractedEntities(raw_response=raw)

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
