from __future__ import annotations

import logging
from pathlib import Path

from application.services.knowledge_service import KnowledgeApplicationService

from application.adapters.review_case_writer_adapter import ReviewCaseWriterAdapter
from application.ports.profile_query import ProfileQueryService
from application.services.review_service import ReviewApplicationService
from core.guards import require
from infrastructure.db.connection import DatabaseConnection, init_db
from infrastructure.db.sqlite_conflict_query import SqliteConflictQuery
from infrastructure.db.sqlite_evidence_query import SqliteEvidenceQuery
from infrastructure.db.sqlite_knowledge_query import SqliteKnowledgeQuery
from infrastructure.db.sqlite_knowledge_unit_of_work import SqliteKnowledgeUnitOfWork
from infrastructure.db.sqlite_profile_query import SqliteProfileQuery
from infrastructure.db.sqlite_provenance_query import SqliteProvenanceQuery
from infrastructure.db.sqlite_review_unit_of_work import SqliteReviewUnitOfWork
from infrastructure.output.conflict_report_json_generator import (
    ConflictReportJsonGenerator,
)
from infrastructure.output.evidence_report_json_generator import (
    EvidenceReportJsonGenerator,
)
from infrastructure.output.fact_export_json_generator import FactExportJsonGenerator
from infrastructure.output.knowledge_report_json_generator import (
    KnowledgeReportJsonGenerator,
)
from infrastructure.output.profile_report_json_generator import (
    ProfileReportJsonGenerator,
)
from infrastructure.output.provenance_report_json_generator import (
    ProvenanceReportJsonGenerator,
)
from output.output_generator import OutputGeneratorRegistry
from output.output_type import OutputType
from pipeline.handler_registry import HandlerRegistry
from pipeline.handlers.document_import_handler import DocumentImportHandler
from pipeline.handlers.entity_resolution_handler import EntityResolutionHandler
from pipeline.handlers.extraction_handler import ExtractionHandler
from pipeline.handlers.fact_acceptance_handler import FactAcceptanceHandler
from pipeline.handlers.knowledge_build_handler import KnowledgeBuildHandler
from pipeline.handlers.ocr_handler import OcrHandler
from pipeline.handlers.output_build_handler import OutputBuildHandler
from pipeline.handlers.profile_build_handler import ProfileBuildHandler
from pipeline.job import JobType
from pipeline.sequential_pipeline_handler import SequentialPipelineHandler
from processing.entity_resolution.entity_resolution_service import (
    EntityResolutionService,
)
from processing.entity_resolution.entity_resolver import EntityResolver
from processing.extraction.extraction_service import ExtractionService
from processing.extraction.extractor_registry import ExtractorRegistry
from processing.fact_acceptance.fact_acceptance_service import FactAcceptanceService
from processing.knowledge_build.knowledge_build_service import KnowledgeBuildService
from processing.ocr.ocr_engine_registry import OcrEngineRegistry
from processing.ocr.ocr_service import OcrService
from processing.output_build.output_build_service import OutputBuildService
from processing.profile_build.profile_build_service import ProfileBuildService

_log = logging.getLogger(__name__)


class Container:

    def __init__(
        self,
        base_output_dir: Path,
        db_path: Path,
        ocr_engine_registry: OcrEngineRegistry,
        extractor_registry: ExtractorRegistry | None = None,
    ) -> None:
        require(isinstance(base_output_dir, Path), "base_output_dir must be a Path")
        require(bool(str(base_output_dir).strip()), "base_output_dir must not be blank")
        require(isinstance(db_path, Path), "db_path must be a Path")
        require(bool(str(db_path).strip()), "db_path must not be blank")
        require(
            isinstance(ocr_engine_registry, OcrEngineRegistry),
            "ocr_engine_registry must be an OcrEngineRegistry",
        )

        self._base_output_dir = base_output_dir

        self._db: DatabaseConnection = init_db(db_path)

        self._knowledge_uow = SqliteKnowledgeUnitOfWork(self._db)
        self._review_uow = SqliteReviewUnitOfWork(self._db)

        self._knowledge_app_service = KnowledgeApplicationService(
            uow=self._knowledge_uow,
        )
        self._review_app_service = ReviewApplicationService(
            uow=self._review_uow,  # type: ignore[arg-type]
        )

        self._knowledge_query = SqliteKnowledgeQuery(self._db)
        self._conflict_query = SqliteConflictQuery(self._db)
        self._evidence_query = SqliteEvidenceQuery(self._db)
        self._provenance_query = SqliteProvenanceQuery(self._db)
        self._profile_query: ProfileQueryService = SqliteProfileQuery(self._db)

        self._ocr_service = OcrService(registry=ocr_engine_registry)

        self._extractor_registry = extractor_registry or ExtractorRegistry()
        self._extraction_service = ExtractionService(
            registry=self._extractor_registry,
        )

        self._entity_resolver = EntityResolver()
        self._entity_resolution_service = EntityResolutionService(
            resolver=self._entity_resolver,
        )

        self._knowledge_build_service = KnowledgeBuildService(
            knowledge_service=self._knowledge_app_service,
        )

        self._profile_build_service = ProfileBuildService(
            knowledge_app_service=self._knowledge_app_service,
        )

        self._review_case_writer = ReviewCaseWriterAdapter(
            service=self._review_app_service,
        )
        self._fact_acceptance_service = FactAcceptanceService(
            knowledge_service=self._knowledge_app_service,
            review_writer=self._review_case_writer,
        )

        self._output_generator_registry = OutputGeneratorRegistry()
        self._output_generator_registry.register(
            OutputType.PROFILE_REPORT,
            ProfileReportJsonGenerator(
                profile_query=self._profile_query,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.FACT_EXPORT,
            FactExportJsonGenerator(
                knowledge_query=self._knowledge_query,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.KNOWLEDGE_REPORT,
            KnowledgeReportJsonGenerator(
                knowledge_query=self._knowledge_query,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.CONFLICT_REPORT,
            ConflictReportJsonGenerator(
                conflict_query=self._conflict_query,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.EVIDENCE_REPORT,
            EvidenceReportJsonGenerator(
                evidence_query=self._evidence_query,
                base_output_dir=base_output_dir,
            ),
        )
        self._output_generator_registry.register(
            OutputType.PROVENANCE_REPORT,
            ProvenanceReportJsonGenerator(
                provenance_query=self._provenance_query,
                base_output_dir=base_output_dir,
            ),
        )

        self._output_build_service = OutputBuildService(
            registry=self._output_generator_registry,
        )

        self._document_import_handler = DocumentImportHandler()
        self._ocr_handler = OcrHandler(ocr_service=self._ocr_service)
        self._extraction_handler = ExtractionHandler(
            extraction_service=self._extraction_service,
        )
        self._entity_resolution_handler = EntityResolutionHandler(
            resolution_service=self._entity_resolution_service,
        )
        self._knowledge_build_handler = KnowledgeBuildHandler(
            knowledge_build_service=self._knowledge_build_service,
        )
        self._fact_acceptance_handler = FactAcceptanceHandler(
            fact_acceptance_service=self._fact_acceptance_service,
        )
        self._profile_build_handler = ProfileBuildHandler(
            profile_build_service=self._profile_build_service,
            knowledge_app_service=self._knowledge_app_service,
        )
        self._output_build_handler = OutputBuildHandler(
            output_build_service=self._output_build_service,
        )

        self._sequential_pipeline_handler = SequentialPipelineHandler(
            handlers={
                "document_import": self._document_import_handler,
                "ocr": self._ocr_handler,
                "extraction": self._extraction_handler,
                "entity_resolution": self._entity_resolution_handler,
                "knowledge_build": self._knowledge_build_handler,
                "fact_acceptance": self._fact_acceptance_handler,
                "profile_build": self._profile_build_handler,
                "output_build": self._output_build_handler,
            }
        )

        _log.info(
            "Container initialised — db=%r  output_dir=%r",
            str(db_path),
            str(base_output_dir),
        )

    @property
    def knowledge_app_service(self) -> KnowledgeApplicationService:
        return self._knowledge_app_service

    @property
    def profile_build_service(self) -> ProfileBuildService:
        return self._profile_build_service

    @property
    def profile_build_handler(self) -> ProfileBuildHandler:
        return self._profile_build_handler

    @property
    def output_build_handler(self) -> OutputBuildHandler:
        return self._output_build_handler

    @property
    def fact_acceptance_handler(self) -> FactAcceptanceHandler:
        return self._fact_acceptance_handler

    @property
    def sequential_pipeline_handler(self) -> SequentialPipelineHandler:
        return self._sequential_pipeline_handler

    def register_handlers(self, handler_registry: HandlerRegistry) -> None:
        require(
            isinstance(handler_registry, HandlerRegistry),
            "handler_registry must be a HandlerRegistry",
        )
        handler_registry.register(JobType.PROFILE_BUILD, self._profile_build_handler)
        handler_registry.register(JobType.OUTPUT_BUILD, self._output_build_handler)
        handler_registry.register(
            JobType.FACT_ACCEPTANCE, self._fact_acceptance_handler
        )
        handler_registry.register(
            JobType.DOCUMENT_PIPELINE, self._sequential_pipeline_handler
        )
