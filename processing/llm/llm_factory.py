from __future__ import annotations

from typing import Any, cast

from models.model_registry import QWEN_0_5B, QWEN_1_5B, get_model_path
from processing.llm.gguf_llm_adapter import GGUFLLMAdapter
from processing.llm.llm_port import LLMPort
from processing.llm.null_llm import NullLLM

_ADVISORY_STOP = ["Note:", "Additionally:", "Furthermore:"]

_ADVISORY_SYSTEM_PROMPT = (
    "You are NASMI Advisory Assistant. "
    "Answer only from the NASMI database context provided by the user prompt. "
    "Do not invent facts. "
    "Separate verified profile facts from pending review candidates. "
    "If profile is missing, explain that accepted facts are required. "
    "Be direct, practical, concise, and answer in English only."
)


def make_fast_llm() -> LLMPort:
    return cast(
        LLMPort,
        GGUFLLMAdapter.cpu(
            model_path=QWEN_0_5B,
            n_ctx=2048,
            max_tokens=200,
            temperature=0.1,
            repeat_penalty=1.3,
            stop=_ADVISORY_STOP,
        ),
    )


def make_quality_llm() -> LLMPort:
    return cast(
        LLMPort,
        GGUFLLMAdapter.cpu(
            model_path=QWEN_1_5B,
            n_ctx=4096,
            max_tokens=400,
            temperature=0.2,
            repeat_penalty=1.3,
            stop=_ADVISORY_STOP,
        ),
    )


def make_advisory_llm() -> LLMPort:
    return cast(
        LLMPort,
        GGUFLLMAdapter.cpu(
            model_path=QWEN_0_5B,
            n_ctx=4096,
            max_tokens=300,
            temperature=0.15,
            repeat_penalty=1.2,
            system_prompt=_ADVISORY_SYSTEM_PROMPT,
            few_shot=[],
            show_thinking=False,
            stop=_ADVISORY_STOP,
        ),
    )


def make_extraction_llm() -> LLMPort:
    return cast(
        LLMPort,
        GGUFLLMAdapter.cpu(
            model_path=QWEN_1_5B,
            n_ctx=8192,
            max_tokens=500,
            temperature=0.0,
            repeat_penalty=1.15,
            few_shot=[],
            show_thinking=False,
            stop=[],
        ),
    )


def make_llm(
    model: str = "qwen-0.5b",
    use_gpu: bool = False,
    **kwargs: Any,
) -> LLMPort:
    path = get_model_path(model)
    if use_gpu:
        return cast(LLMPort, GGUFLLMAdapter.gpu(model_path=path, **kwargs))
    return cast(LLMPort, GGUFLLMAdapter.cpu(model_path=path, **kwargs))


def make_null_llm() -> LLMPort:
    return NullLLM()
