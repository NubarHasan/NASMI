from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMResponse:
    raw_text: str
    raw: dict[str, Any] = field(default_factory=dict)
    failure: str | None = None

    @classmethod
    def empty(cls) -> LLMResponse:
        return cls(raw_text="")

    @classmethod
    def from_error(cls, message: str) -> LLMResponse:
        return cls(raw_text="", failure=message)

    @property
    def has_error(self) -> bool:
        return self.failure is not None

    @property
    def is_empty(self) -> bool:
        return not self.raw_text.strip()
