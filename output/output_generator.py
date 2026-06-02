from typing import Protocol, runtime_checkable

from core.validation import require

from output.output_document import OutputDocument
from output.output_request import OutputRequest
from output.output_type import OutputType


@runtime_checkable
class OutputGenerator(Protocol):
    def generate(
        self,
        request: OutputRequest,
    ) -> OutputDocument: ...


class OutputGeneratorRegistry:
    def __init__(self) -> None:
        self._generators: dict[OutputType, OutputGenerator] = {}

    def register(
        self,
        output_type: OutputType,
        generator: OutputGenerator,
    ) -> None:
        require(
            isinstance(output_type, OutputType),
            "output_type must be an OutputType",
        )
        require(
            isinstance(generator, OutputGenerator),
            f"generator must implement OutputGenerator Protocol, got: {type(generator)!r}",
        )
        require(
            output_type not in self._generators,
            f"OutputGenerator already registered for: {output_type!r}",
        )
        self._generators[output_type] = generator

    def resolve(self, output_type: OutputType) -> OutputGenerator:
        require(
            isinstance(output_type, OutputType),
            "output_type must be an OutputType",
        )
        require(
            output_type in self._generators,
            f"No OutputGenerator registered for: {output_type!r}",
        )
        return self._generators[output_type]

    def is_registered(self, output_type: OutputType) -> bool:
        return output_type in self._generators

    def registered_types(self) -> frozenset[OutputType]:
        return frozenset(self._generators)
