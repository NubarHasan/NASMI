from dataclasses import dataclass, field
from knowledge.knowledge_objects import KnowledgeObject, FieldType
from cognitive.context_fusion import FusedContext
from llm.ollama_client import OllamaClient
from core.events import Event, EventType
from core.event_bus import bus


PREDICTION_PROMPTS: dict[str, str] = {
    "risk_summary": "Summarize the risk profile of this person based on the following data:",
    "next_action": "Based on the context below, what is the most likely next administrative action needed?",
    "data_gap": "Identify missing or incomplete information based on the following profile:",
    "life_stage": "Determine the current life stage of this person based on the available data:",
}


@dataclass
class Prediction:
    prediction_type: str
    result: str
    confidence: float
    context_used: int

    def to_dict(self) -> dict:
        return {
            "type": self.prediction_type,
            "result": self.result,
            "confidence": self.confidence,
            "context_used": self.context_used,
        }


class PredictionEngine:

    DEFAULT_MODEL = "llama3"

    def __init__(self):
        self._client: OllamaClient = OllamaClient()

    def predict(
        self,
        prediction_type: str,
        context: FusedContext,
        model: str = DEFAULT_MODEL,
    ) -> Prediction:

        prompt_prefix = PREDICTION_PROMPTS.get(
            prediction_type, "Analyze the following data:"
        )
        context_text = self._build_context_text(context)
        prompt = f"{prompt_prefix}\n\n{context_text}\n\nAnswer concisely:"

        result = self._client.generate(prompt=prompt, model=model)

        prediction = Prediction(
            prediction_type=prediction_type,
            result=result,
            confidence=context.trust_score,
            context_used=len(context.objects),
        )

        bus.publish(
            Event(
                event_type=EventType.PREDICTION_GENERATED,
                payload=prediction.to_dict(),
                source="prediction_engine",
            )
        )

        return prediction

    def predict_all(
        self, context: FusedContext, model: str = DEFAULT_MODEL
    ) -> list[Prediction]:
        return [self.predict(p_type, context, model) for p_type in PREDICTION_PROMPTS]

    def _build_context_text(self, context: FusedContext) -> str:
        lines = [
            f"Owner: {context.owner_id}",
            f"Trust Score: {context.trust_score}",
            f"Coverage: {context.coverage}",
            f"Life Events: {[c.label for c in context.clusters]}",
            "",
            "Data Fields:",
        ]

        for obj in context.objects:
            lines.append(
                f"  - [{obj.field_type.value}] {obj.value} (confidence: {obj.confidence.final})"
            )

        return "\n".join(lines)
