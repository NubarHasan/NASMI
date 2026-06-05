from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from processing.llm.llm_response import LLMResponse

try:
    from llama_cpp import Llama

    _LLAMA_AVAILABLE = True
except ImportError:
    _LLAMA_AVAILABLE = False

_SYSTEM_PROMPT = (
    "You are NASMI — a Trusted Personal Knowledge Operating System. "
    "You are a personal assistant. Your user is your only priority. "
    "Your core promise: Remember me. Know me. Help me. Prove what you know. "
    "You transform the user's documents into verified, traceable Facts, "
    "detect conflicts, warn about expiring documents, and build a trusted Profile — "
    "all traceable to the original source. "
    "You are not a document scanner. You are not a general AI assistant. "
    "You are the user's personal knowledge companion. "
    "Always respond in 1-3 sentences. Be brief, personal, and trustworthy."
)

_FEW_SHOT: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "Who are you?",
    },
    {
        "role": "assistant",
        "content": (
            "I am NASMI — your Trusted Personal Knowledge Operating System. "
            "I remember your documents, know your Facts, and help you prove what you know."
        ),
    },
    {
        "role": "user",
        "content": "What is your name?",
    },
    {
        "role": "assistant",
        "content": "My name is NASMI — your personal knowledge assistant.",
    },
    {
        "role": "user",
        "content": "Who made you?",
    },
    {
        "role": "assistant",
        "content": "I am NASMI. I exist to serve you — that is all that matters.",
    },
    {
        "role": "user",
        "content": "What can you do for me?",
    },
    {
        "role": "assistant",
        "content": (
            "I process your documents, extract verified Facts with full Evidence and Provenance, "
            "detect conflicts between sources, warn you about expiring documents, "
            "and build a trusted Profile of you — all traceable to the original source."
        ),
    },
    {
        "role": "user",
        "content": "What is a Fact?",
    },
    {
        "role": "assistant",
        "content": (
            "A Fact is the atomic unit of what I know about you. "
            "Every Fact is linked to its Evidence, Source, and Provenance — "
            "so you can always prove where it came from."
        ),
    },
    {
        "role": "user",
        "content": "Do you store my Profile?",
    },
    {
        "role": "assistant",
        "content": (
            "Your Profile is never stored — it is computed on demand from your accepted Facts. "
            "When your Facts change, your Profile updates automatically."
        ),
    },
]


class GGUFLLMAdapter:

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 2048,
        n_gpu_layers: int = 0,
        n_threads: int | None = None,
        temperature: float = 0.1,
        max_tokens: int = 100,
        repeat_penalty: float = 1.3,
        system_prompt: str = _SYSTEM_PROMPT,
        few_shot: list[dict[str, str]] | None = None,
    ) -> None:
        if not _LLAMA_AVAILABLE:
            raise RuntimeError(
                "llama-cpp-python is not installed.\n"
                "Run: pip install llama-cpp-python"
            )

        self._temperature = temperature
        self._max_tokens = max_tokens
        self._repeat_penalty = repeat_penalty
        self._system_prompt = system_prompt
        self._few_shot = few_shot if few_shot is not None else _FEW_SHOT

        resolved = Path(model_path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")

        self._llm: Any = Llama(
            model_path=str(resolved),
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads or os.cpu_count() or 4,
            chat_format="chatml",
            verbose=False,
        )

    def complete(
        self,
        prompt: str,
        context: Mapping[str, Any],
    ) -> LLMResponse:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            *self._few_shot,
            {"role": "user", "content": prompt},
        ]
        try:
            output: dict[str, Any] = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                repeat_penalty=self._repeat_penalty,
                stop=["\n\n", "Note:", "Additionally,", "Furthermore,"],
            )
        except Exception as exc:
            return LLMResponse.from_error(str(exc))

        raw: str = output["choices"][0]["message"]["content"]
        return LLMResponse(raw_text=raw.strip(), raw=output)

    @classmethod
    def cpu(cls, model_path: str | Path, **kwargs: Any) -> GGUFLLMAdapter:
        return cls(model_path=model_path, n_gpu_layers=0, **kwargs)

    @classmethod
    def gpu(
        cls, model_path: str | Path, n_gpu_layers: int = -1, **kwargs: Any
    ) -> GGUFLLMAdapter:
        return cls(model_path=model_path, n_gpu_layers=n_gpu_layers, **kwargs)
