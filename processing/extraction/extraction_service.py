from __future__ import annotations

import logging

from core.guards import require
from core.types import DocumentId, ExtractorId, SourceId
from processing.extraction.extraction_request import ExtractionRequest
from processing.extraction.extraction_result import ExtractionResult
from processing.extraction.extractor_registry import ExtractorRegistry

_log = logging.getLogger(__name__)

_UNKNOWN_EXTRACTOR = ExtractorId("unknown")


class ExtractionService:

    def __init__(self, registry: ExtractorRegistry) -> None:
        require(
            isinstance(registry, ExtractorRegistry),
            "registry must be an ExtractorRegistry",
        )
        self._registry = registry

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        require(
            isinstance(request, ExtractionRequest),
            "request must be an ExtractionRequest",
        )
        document_id: DocumentId = request.content.document_id
        source_id: SourceId = request.content.source_id
        document_type: str | None = request.content.document_type

        if not document_type:
            _log.warning(
                "extraction request carries no document_type — source_id=%r",
                source_id,
            )
            return ExtractionResult.failure(
                document_id=document_id,
                source_id=source_id,
                extractor_id=_UNKNOWN_EXTRACTOR,
                metadata={"reason": "document_type is missing"},
            )

        extractor = self._registry.resolve(document_type)

        if extractor is None:
            _log.warning(
                "no extractor registered for document_type %r",
                document_type,
            )
            return ExtractionResult.failure(
                document_id=document_id,
                source_id=source_id,
                extractor_id=_UNKNOWN_EXTRACTOR,
                metadata={
                    "reason": f"no extractor for document_type {document_type!r}"
                },
            )

        if not extractor.can_handle(request):
            _log.warning(
                "extractor %r refused request for document_type %r",
                extractor.extractor_id,
                document_type,
            )
            return ExtractionResult.failure(
                document_id=document_id,
                source_id=source_id,
                extractor_id=extractor.extractor_id,
                metadata={
                    "reason": (
                        f"extractor {extractor.extractor_id!r} "
                        f"refused document_type {document_type!r}"
                    )
                },
            )

        _log.debug(
            "dispatching document_type %r to extractor %r",
            document_type,
            extractor.extractor_id,
        )
        return extractor.extract(request)
