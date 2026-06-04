from __future__ import annotations

import logging
from dataclasses import dataclass

from core.guards import require
from core.identifiers import is_valid_entity_id
from core.time import utcnow
from core.types import EntityId
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_generator import OutputGeneratorRegistry
from output.output_request import OutputRequest
from output.output_type import OutputType

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutputBuildResult:
    entity_id: EntityId
    documents: tuple[OutputDocument, ...]
    requested_count: int
    succeeded_count: int
    failed_count: int

    @property
    def is_complete(self) -> bool:
        return self.failed_count == 0 and self.succeeded_count > 0


class OutputBuildService:

    def __init__(self, registry: OutputGeneratorRegistry) -> None:
        require(
            isinstance(registry, OutputGeneratorRegistry),
            "registry must be an OutputGeneratorRegistry",
        )
        self._registry = registry

    def build(
        self,
        entity_id: EntityId,
        output_types: tuple[OutputType, ...],
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> OutputBuildResult:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(len(output_types) > 0, "output_types must not be empty")
        require(
            all(isinstance(t, OutputType) for t in output_types),
            "all output_types must be OutputType instances",
        )
        require(
            isinstance(output_format, OutputFormat),
            "output_format must be an OutputFormat",
        )

        documents: list[OutputDocument] = []
        failed = 0

        for output_type in output_types:
            if not self._registry.is_registered(output_type):
                _log.warning(
                    "no generator registered for output_type=%r — skipping",
                    output_type,
                )
                failed += 1
                continue

            request = OutputRequest(
                subject_id=entity_id,
                output_type=output_type,
                output_format=output_format,
                requested_at=utcnow(),
            )

            try:
                generator = self._registry.resolve(output_type)
                doc = generator.generate(request)
                documents.append(doc)
                _log.info(
                    "generated output type=%r format=%r entity=%r",
                    output_type,
                    output_format,
                    entity_id,
                )
            except Exception:
                _log.exception(
                    "generator failed for output_type=%r entity=%r",
                    output_type,
                    entity_id,
                )
                failed += 1

        return OutputBuildResult(
            entity_id=entity_id,
            documents=tuple(documents),
            requested_count=len(output_types),
            succeeded_count=len(documents),
            failed_count=failed,
        )
