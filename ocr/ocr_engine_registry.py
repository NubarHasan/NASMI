from __future__ import annotations

from core.guards import require
from ocr.ocr_engine import OcrEngine


class OcrEngineRegistry:

    def __init__(
        self,
        default_engine_name: str,
    ) -> None:
        require(
            isinstance(default_engine_name, str), "default_engine_name must be a str"
        )
        require(
            bool(default_engine_name.strip()), "default_engine_name must not be empty"
        )

        self._engines: dict[str, OcrEngine] = {}
        self._default_engine_name: str = default_engine_name

    def register(
        self,
        engine: OcrEngine,
    ) -> None:
        require(
            isinstance(engine, OcrEngine), "engine must implement OcrEngine Protocol"
        )

        name = engine.engine_name

        require(isinstance(name, str), "engine.engine_name must be a str")
        require(bool(name.strip()), "engine.engine_name must not be empty")
        require(name not in self._engines, f"engine already registered: {name!r}")

        self._engines[name] = engine

    def unregister(
        self,
        name: str,
    ) -> None:
        require(isinstance(name, str), "name must be a str")
        require(name in self._engines, f"engine not registered: {name!r}")
        require(
            len(self._engines) > 1,
            "cannot unregister the last registered engine",
        )

        del self._engines[name]

        if name == self._default_engine_name:
            self._default_engine_name = next(iter(self._engines))

    def get(
        self,
        name: str,
    ) -> OcrEngine:
        require(isinstance(name, str), "name must be a str")
        require(name in self._engines, f"engine not registered: {name!r}")

        return self._engines[name]

    def default(self) -> OcrEngine:
        require(
            self._default_engine_name in self._engines,
            f"default engine not registered: {self._default_engine_name!r}",
        )

        return self._engines[self._default_engine_name]

    def set_default(
        self,
        name: str,
    ) -> None:
        require(isinstance(name, str), "name must be a str")
        require(name in self._engines, f"engine not registered: {name!r}")

        self._default_engine_name = name

    def has(
        self,
        name: str,
    ) -> bool:
        return name in self._engines

    @property
    def engines(self) -> tuple[OcrEngine, ...]:
        return tuple(self._engines.values())

    @property
    def registered_names(self) -> tuple[str, ...]:
        return tuple(self._engines.keys())

    @property
    def default_engine_name(self) -> str:
        return self._default_engine_name

    @property
    def engine_count(self) -> int:
        return len(self._engines)

    @property
    def is_empty(self) -> bool:
        return len(self._engines) == 0
