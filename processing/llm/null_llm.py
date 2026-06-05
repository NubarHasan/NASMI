from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from processing.llm.llm_response import LLMResponse


class NullLLM:
    def complete(
        self,
        prompt: str,
        context: Mapping[str, Any],
    ) -> LLMResponse:
        return LLMResponse.empty()
