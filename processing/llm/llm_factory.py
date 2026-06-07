from __future__ import annotations

from typing import Any, cast

from models.model_registry import QWEN_0_5B, QWEN_1_5B, get_model_path
from processing.llm.gguf_llm_adapter import GGUFLLMAdapter
from processing.llm.llm_port import LLMPort
from processing.llm.null_llm import NullLLM

_ADVISORY_STOP = ["Note:", "Additionally,", "Furthermore,"]


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
