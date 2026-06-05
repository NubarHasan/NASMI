from __future__ import annotations

from enum import StrEnum


class LLMRole(StrEnum):
    EXTRACTION_ASSISTANT = "extraction_assistant"
    KNOWLEDGE_ASSISTANT = "knowledge_assistant"
