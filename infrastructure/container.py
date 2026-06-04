from __future__ import annotations

import logging
from pathlib import Path

from pipeline.handler_registry import HandlerRegistry

from application.ports.profile_query import ProfileQueryService
from core.guards import require
from core.types import EntityId
from infrastructure.output.conflict_report_json_generator import (
    ConflictReportJsonGenerator,
)
from infrastructure.output.evidence_report_json_generator import (
    EvidenceReportJsonGenerator,
)
from infrastructure.output.fact_export_json_generator import (
    FactExportJsonGenerator,
)
from infrastructure.output.knowledge_report_json_generator import (
    KnowledgeReportJsonGenerator,
)
from infrastructure.output.profile_report_json_generator import (
    ProfileReportJsonGenerator,
)
from infrastructure.output.provenance_report_json_generator import (
    ProvenanceReportJsonGenerator,
)
from knowledge.knowledge_service import KnowledgeService
from knowledge.profile import Profile
from output.output_generator import OutputGeneratorRegistry
from output.output_type import OutputType
from processing.output_build.output_build_handler import OutputBuildHandler
from processing.output_build.output_build_service import OutputBuildService
from processing.profile_build.profile_build_service import ProfileBuildService

_log = logging.getLogger(__name__)


class _ProfileQueryAdapter:

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        entity_type: str = "person",
        display_name: str = "Unknown",
    ) -> None:
        self._ks = knowledge_service
        self._entity_type = entity_type
        self._display_name = display_name

    def get_profile(self, entity_id: EntityId) -> Profile | None:
        entity = self._ks.get_entity(entity_id)
        if entity is None:
            return None
        return self._ks.build_profile(
            entity_id=entity_id,
            entity_type=entity.entity_type,
            display_name=entity.display_name,
        )


class Container:

    def __init__(self, base_output_dir: Path) -> None:
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            bool(str(base_output_dir).strip()),
            "base_output_dir must not be blank",
        )

        self._base_output_dir = base_output_dir

        self._knowledge_service = KnowledgeService()

        self._profile_query_adapter: ProfileQueryService = _ProfileQueryAdapter(
            knowledge_service=self._knowledge_service,
        )

        self._profile_build_service = ProfileBuildService(
            knowledge_service=self._knowledge_service,
        )

        self._output_generator_registry = OutputGeneratorRegistry()

        self._output_generator_registry.register(
            OutputType.PROFILE_REPORT,
            ProfileReportJsonGenerator(
                profile_query=self._profile_query_adapter,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.FACT_EXPORT,
            FactExportJsonGenerator(
                knowledge_query=self._knowledge_service,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.KNOWLEDGE_REPORT,
            KnowledgeReportJsonGenerator(
                knowledge_query=self._knowledge_service,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.CONFLICT_REPORT,
            ConflictReportJsonGenerator(
                conflict_query=self._knowledge_service,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.EVIDENCE_REPORT,
            EvidenceReportJsonGenerator(
                evidence_query=self._knowledge_service,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.PROVENANCE_REPORT,
            ProvenanceReportJsonGenerator(
                provenance_query=self._knowledge_service,
                base_output_dir=base_output_dir,
            ),
        )

        _log.debug(
            "OutputGeneratorRegistry ready — registered types: %r",
            list(self._output_generator_registry.registered_types()),
        )

        self._output_build_service = OutputBuildService(
            registry=self._output_generator_registry,
        )

        self._output_build_handler = OutputBuildHandler(
            output_build_service=self._output_build_service,
        )

        _log.info(
            "Container initialised — base_output_dir=%r",
            str(base_output_dir),
        )

    @property
    def knowledge_service(self) -> KnowledgeService:
        return self._knowledge_service

    @property
    def profile_build_service(self) -> ProfileBuildService:
        return self._profile_build_service

    @property
    def output_build_handler(self) -> OutputBuildHandler:
        return self._output_build_handler

    def register_handlers(self, handler_registry: HandlerRegistry) -> None:
        require(
            isinstance(handler_registry, HandlerRegistry),
            "handler_registry must be a HandlerRegistry",
        )
        handler_registry.register(self._output_build_handler)
        _log.debug("OutputBuildHandler registered in HandlerRegistry")
