from application.application_error import ApplicationError
from application.error_code import ErrorCode
from application.result import Failure, Result, Success
from core.exceptions import ValidationError
from core.guards import require
from output.output_document import OutputDocument
from output.output_generator import OutputGeneratorRegistry
from output.output_request import OutputRequest


class OutputService:

    def __init__(self, registry: OutputGeneratorRegistry) -> None:
        require(
            isinstance(registry, OutputGeneratorRegistry),
            "registry must be an OutputGeneratorRegistry",
        )
        self._registry = registry

    def generate_output(self, request: OutputRequest) -> Result[OutputDocument]:
        require(isinstance(request, OutputRequest), "request must be an OutputRequest")

        try:
            generator = self._registry.resolve(request.output_type)
        except ValidationError:
            return Failure(
                ApplicationError(
                    code=ErrorCode.OUTPUT_GENERATOR_NOT_FOUND,
                    message=f"no generator registered for {request.output_type}",
                )
            )

        try:
            document = generator.generate(request)
        except Exception as exc:
            return Failure(
                ApplicationError(
                    code=ErrorCode.OUTPUT_GENERATION_FAILED,
                    message=f"generator failed for {request.output_type}: {exc}",
                )
            )

        return Success(document)
