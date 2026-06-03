from __future__ import annotations

import logging
import threading

from core.exceptions import ValidationError
from core.guards import require
from core.types import ExtractorId
from processing.extraction.extractor import Extractor

_log = logging.getLogger(__name__)


class ExtractorRegistry:

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_id: dict[ExtractorId, Extractor] = {}
        self._by_doc_type: dict[str, Extractor] = {}

    def register(self, extractor: Extractor) -> None:
        require(
            isinstance(extractor, Extractor),
            "extractor must implement the Extractor protocol",
        )
        with self._lock:
            eid = extractor.extractor_id
            require(
                bool(eid not in self._by_id),
                f"extractor already registered: {eid!r}",
            )
            conflicts = [
                dt
                for dt in extractor.supported_document_types
                if dt in self._by_doc_type
            ]
            if conflicts:
                raise ValidationError(
                    f"document_type(s) already claimed: {conflicts!r}"
                )
            self._by_id[eid] = extractor
            for doc_type in extractor.supported_document_types:
                self._by_doc_type[doc_type] = extractor
            _log.debug(
                "registered extractor %r for types %r",
                eid,
                sorted(extractor.supported_document_types),
            )

    def get(self, extractor_id: ExtractorId) -> Extractor | None:
        with self._lock:
            return self._by_id.get(extractor_id)

    def resolve(self, document_type: str) -> Extractor | None:
        require(
            bool(isinstance(document_type, str) and document_type),
            "document_type must be a non-empty string",
        )
        with self._lock:
            return self._by_doc_type.get(document_type)

    def all(self) -> list[Extractor]:
        with self._lock:
            return list(self._by_id.values())

    def registered_document_types(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._by_doc_type)

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)

    def __contains__(self, extractor_id: ExtractorId) -> bool:
        with self._lock:
            return extractor_id in self._by_id
