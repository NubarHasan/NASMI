from __future__ import annotations

from models.model_registry import QWEN_0_5B, QWEN_1_5B, get_model_path
from processing.llm.gguf_llm_adapter import GGUFLLMAdapter
from processing.llm.llm_port import LLMPort
from processing.llm.null_llm import NullLLM


def make_fast_llm() -> LLMPort:

    return GGUFLLMAdapter.cpu(
        model_path=QWEN_0_5B,
        n_ctx=1024,
        max_tokens=150,
        temperature=0.1,
        repeat_penalty=1.3,
    )


def make_quality_llm() -> LLMPort:

    return GGUFLLMAdapter.cpu(
        model_path=QWEN_1_5B,
        n_ctx=2048,
        max_tokens=300,
        temperature=0.2,
        repeat_penalty=1.3,
    )


def make_llm(
    model: str = "qwen-0.5b",
    use_gpu: bool = False,
    **kwargs: object,
) -> LLMPort:
    path = get_model_path(model)
    if use_gpu:
        return GGUFLLMAdapter.gpu(model_path=path, **kwargs)  # type: ignore[arg-type]
    return GGUFLLMAdapter.cpu(model_path=path, **kwargs)  # type: ignore[arg-type]


def make_null_llm() -> LLMPort:
    return NullLLM()
