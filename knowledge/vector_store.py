import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from llm.ollama_client import OllamaClient
from core.events import Event, EventType
from core.event_bus import bus


@dataclass
class VectorEntry:
    id:          str
    text:        str
    embedding:   list[float]
    metadata:    dict          = field(default_factory=dict)
    created_at:  datetime      = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            'id':         self.id,
            'text':       self.text,
            'metadata':   self.metadata,
            'created_at': self.created_at.isoformat(),
        }


@dataclass
class SearchResult:
    entry:      VectorEntry
    score:      float

    def to_dict(self) -> dict:
        return {
            'score':    round(self.score, 4),
            'text':     self.entry.text,
            'metadata': self.entry.metadata,
        }


class VectorStore:

    EMBED_MODEL = 'nomic-embed-text'

    def __init__(self):
        self._store:  list[VectorEntry] = []
        self._client: OllamaClient      = OllamaClient()

    def add(self, text: str, metadata: dict | None = None) -> VectorEntry:
        embedding = self._embed(text)
        entry     = VectorEntry(
            id        = str(uuid.uuid4()),
            text      = text,
            embedding = embedding,
            metadata  = metadata or {},
        )
        self._store.append(entry)
        return entry

    def add_batch(self, items: list[dict]) -> list[VectorEntry]:
        return [self.add(item['text'], item.get('metadata')) for item in items]

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not self._store:
            return []

        query_vec = self._embed(query)
        scored    = [
            SearchResult(entry=entry, score=self._cosine(query_vec, entry.embedding))
            for entry in self._store
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def rag_query(self, query: str, top_k: int = 5, model: str = 'llama3') -> dict:
        results = self.search(query, top_k)

        if not results:
            return {'answer': 'No relevant documents found.', 'sources': []}

        context = '\n\n'.join(
            f'[Source {i+1}]: {r.entry.text}'
            for i, r in enumerate(results)
        )

        prompt = (
            f'You are a helpful assistant. Answer the question using only the provided context.\n\n'
            f'Context:\n{context}\n\n'
            f'Question: {query}\n\n'
            f'Answer:'
        )

        answer = self._client.generate(prompt=prompt, model=model)

        bus.publish(Event(
            event_type = EventType.PREDICTION_GENERATED,
            payload    = {
                'query':        query,
                'sources_used': len(results),
                'model':        model,
            },
            source = 'vector_store',
        ))

        return {
            'answer':  answer,
            'sources': [r.to_dict() for r in results],
        }

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

    def _embed(self, text: str) -> list[float]:
        return self._client.embed(text=text, model=self.EMBED_MODEL)  # type: ignore[attr-defined]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot    = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x ** 2 for x in a))
        norm_b = math.sqrt(sum(x ** 2 for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
