from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from processing.llm.llm_response import LLMResponse


@runtime_checkable
class LLMPort(Protocol):
    def complete(
        self,
        prompt: str,
        context: Mapping[str, Any],
    ) -> LLMResponse: ...
