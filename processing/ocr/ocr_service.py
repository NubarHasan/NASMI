from __future__ import annotations

from core.guards import require
from processing.ocr.ocr_engine_registry import OcrEngineRegistry
from processing.ocr.ocr_request import OcrRequest
from processing.ocr.ocr_result import OcrResult


class OcrService:

    def __init__(self, registry: OcrEngineRegistry) -> None:
        require(
            isinstance(registry, OcrEngineRegistry),
            "registry must be an OcrEngineRegistry",
        )
        self._registry = registry

    def process(
        self,
        request: OcrRequest,
        engine_name: str | None = None,
    ) -> OcrResult:
        if engine_name is None:
            engine = self._registry.default()
        else:
            engine = self._registry.get(engine_name)

        return engine.process(request)
