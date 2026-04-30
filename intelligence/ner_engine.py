import re
import json
import spacy
from dataclasses import dataclass, field
from llm.ollama_client import OllamaClient
from config import MODELS


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

SPACY_BLACKLIST = {
    'passport', 'document', 'name', 'nationality', 'address',
    'phone', 'email', 'employer', 'id', 'number', 'date', 'birth',
    'issue', 'expiry', 'type', 'gender', 'sex', 'age', 'place',
}


@dataclass
class ExtractedEntities:
    full_name:       str | None = None
    date_of_birth:   str | None = None
    nationality:     str | None = None
    id_number:       str | None = None
    passport_number: str | None = None
    address:         str | None = None
    phone:           str | None = None
    email:           str | None = None
    employer:        str | None = None
    issue_date:      str | None = None
    expiry_date:     str | None = None
    document_type:   str | None = None
    extra:           dict = field(default_factory=dict)
    confidence:      float = 0.0
    raw_response:    str = ''

    def to_dict(self) -> dict:
        return {
            'full_name':       self.full_name,
            'date_of_birth':   self.date_of_birth,
            'nationality':     self.nationality,
            'id_number':       self.id_number,
            'passport_number': self.passport_number,
            'address':         self.address,
            'phone':           self.phone,
            'email':           self.email,
            'employer':        self.employer,
            'issue_date':      self.issue_date,
            'expiry_date':     self.expiry_date,
            'document_type':   self.document_type,
            'extra':           self.extra,
            'confidence':      self.confidence,
        }


class NEREngine:

    _nlp_de = None
    _nlp_en = None

    def __init__(self) -> None:
        self.client = OllamaClient()

        if NEREngine._nlp_de is None:
            try:
                NEREngine._nlp_de = spacy.load('de_core_news_lg')
            except Exception:
                NEREngine._nlp_de = None

        if NEREngine._nlp_en is None:
            try:
                NEREngine._nlp_en = spacy.load('en_core_web_lg')
            except Exception:
                NEREngine._nlp_en = None

    def extract(self, text: str, doc_type: str = 'unknown') -> ExtractedEntities:
        entities = ExtractedEntities(document_type=doc_type)

        self._apply_regex(text, entities)
        self._apply_spacy(text, entities)

        entities.confidence = self._score(entities)

        if entities.confidence < 0.85:
            self._apply_ollama(text, entities)
            entities.confidence = self._score(entities)

        return entities

    def _apply_regex(self, text: str, e: ExtractedEntities) -> None:
        email_match = re.search(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', text)
        if email_match and not e.email:
            e.email = email_match.group(0)

        phone_match = re.search(
            r'(?<!\d)(\+?[\d][\d\s\-]{7,}\d)(?!\s*[-\/]\s*\d{2})',
            text
        )
        if phone_match and not e.phone:
            candidate = phone_match.group(1)
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', candidate.strip()):
                e.phone = candidate

        dob_match = re.search(
            r'\b(?:date\s*of\s*birth|dob|geboren|geburtsdatum)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}[.\/]\d{2}[.\/]\d{4})\b',
            text, re.IGNORECASE
        )
        if dob_match and not e.date_of_birth:
            e.date_of_birth = dob_match.group(1)
        elif not e.date_of_birth:
            plain_date = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
            if plain_date:
                e.date_of_birth = plain_date.group(1)

        id_match = re.search(r'\bID[:\s]*([A-Z0-9\-]+)\b', text, re.IGNORECASE)
        if id_match and not e.id_number:
            e.id_number = id_match.group(1)

        passport_match = re.search(
            r'\bPassport\s*(?:No|Number|#)?[:\s]+([A-Z]{1,3}\d{4,}|\d{4,}[A-Z]{1,3})\b',
            text, re.IGNORECASE
        )
        if passport_match and not e.passport_number:
            e.passport_number = passport_match.group(1)

        iban_match = re.search(r'\b([A-Z]{2}\d{2}[\dA-Z]{11,})\b', text)
        if iban_match and not e.extra.get('iban'):
            e.extra['iban'] = iban_match.group(1)

        tax_match = re.search(r'\b(\d{2}\s?\d{3}\s?\d{5})\b', text)
        if tax_match and not e.extra.get('tax_id'):
            e.extra['tax_id'] = tax_match.group(1)

    def _apply_spacy(self, text: str, e: ExtractedEntities) -> None:
        for nlp in [NEREngine._nlp_de, NEREngine._nlp_en]:
            if nlp is None:
                continue

            doc = nlp(text[:3000])

            for ent in doc.ents:
                val = ent.text.strip()
                if val.lower() in SPACY_BLACKLIST:
                    continue

                if ent.label_ in ('PER', 'PERSON') and not e.full_name:
                    e.full_name = val
                elif ent.label_ in ('GPE', 'LOC') and not e.address:
                    e.address = val
                elif ent.label_ == 'ORG' and not e.employer:
                    e.employer = val
                elif ent.label_ == 'NORP' and not e.nationality:
                    e.nationality = val

    def _apply_ollama(self, text: str, e: ExtractedEntities) -> None:
        try:
            prompt = ENTITY_PROMPT.format(text=text[:2000])

            raw = self.client.generate(
                prompt=prompt,
                model=MODELS['text'],
                system=SYSTEM_PROMPT,
            )

            e.raw_response = raw

            start = raw.find('{')
            end   = raw.rfind('}') + 1
            if start == -1 or end == 0:
                return

            data = json.loads(raw[start:end])

            e.full_name       = e.full_name       or data.get('full_name')
            e.date_of_birth   = e.date_of_birth   or data.get('date_of_birth')
            e.nationality     = e.nationality     or data.get('nationality')
            e.id_number       = e.id_number       or data.get('id_number')
            e.passport_number = e.passport_number or data.get('passport_number')
            e.address         = e.address         or data.get('address')
            e.phone           = e.phone           or data.get('phone')
            e.email           = e.email           or data.get('email')
            e.employer        = e.employer        or data.get('employer')
            e.issue_date      = e.issue_date      or data.get('issue_date')
            e.expiry_date     = e.expiry_date     or data.get('expiry_date')
            e.document_type   = e.document_type   or data.get('document_type')

            extra = data.get('extra', {})
            if isinstance(extra, dict):
                e.extra.update(extra)

        except Exception as ex:
            print(f'[NER] Ollama failed: {ex}')

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