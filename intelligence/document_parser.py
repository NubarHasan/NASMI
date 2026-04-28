from dataclasses import dataclass, field
from core.document_loader import DocumentLoader, LoadedDocument
from core.text_extractor import TextExtractor, ExtractedText
from intelligence.ner_engine import NEREngine, ExtractedEntities
from core.events import Event, EventType
from core.event_bus import bus


@dataclass
class ParsedDocument:
    loaded: LoadedDocument
    extracted: ExtractedText
    entities: ExtractedEntities
    metadata: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.entities.confidence >= 0.5

    def to_dict(self) -> dict:
        return {
            "filename": self.loaded.filename,
            "file_hash": self.loaded.file_hash,
            "file_size": self.loaded.file_size,
            "page_count": self.extracted.metadata.get("page_count", 0),
            "entities": self.entities.to_dict(),
            "is_valid": self.is_valid,
            "metadata": self.metadata,
        }


class DocumentParser:

    def __init__(self) -> None:
        self.loader = DocumentLoader()
        self.extractor = TextExtractor()
        self.ner = NEREngine()

    def parse(self, file_path: str) -> ParsedDocument:
        loaded = self.loader.load(file_path)
        extracted = self.extractor.extract(loaded)
        full_text = extracted.full_text
        entities = self.ner.extract(full_text)

        parsed = ParsedDocument(
            loaded=loaded,
            extracted=extracted,
            entities=entities,
            metadata={"model_used": self.ner.client.models["text"]},
        )

        bus.publish(
            Event(
                event_type=EventType.ENTITIES_EXTRACTED,
                payload=parsed.to_dict(),
                source="document_parser",
            )
        )

        return parsed
