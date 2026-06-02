from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.constants import SystemComponent


class NasmiError(Exception):
    def __init__(
        self,
        message: str,
        component: SystemComponent | None = None,
        entity_id: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.component = component
        self.entity_id = entity_id
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now(UTC).isoformat()

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"component={self.component!r}, "
            f"entity_id={self.entity_id!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "component": self.component.value if self.component else None,
            "entity_id": self.entity_id,
            "error_code": self.error_code,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class CoreError(NasmiError):
    pass


class ConfigurationError(CoreError):
    pass


class InvalidConfigurationError(ConfigurationError):
    pass


class MissingConfigurationError(ConfigurationError):
    pass


class ValidationError(CoreError):
    pass


class StateError(CoreError):
    pass


class NotFoundError(CoreError):
    pass


class AlreadyExistsError(CoreError):
    pass


class PermissionError(CoreError):
    pass


class StorageError(CoreError):
    pass


class DatabaseError(CoreError):
    pass


class IntegrityError(CoreError):
    pass


class ArchiveError(CoreError):
    pass


class ProcessingError(CoreError):
    pass


class PipelineError(CoreError):
    pass


class LockError(CoreError):
    pass


class TimeoutError(CoreError):
    pass


class RetryError(CoreError):
    pass


class AuditError(CoreError):
    pass


class KnowledgeError(CoreError):
    pass


class PackageError(CoreError):
    pass


class ExportError(CoreError):
    pass


class FileSystemError(CoreError):
    pass


class TransactionError(CoreError):
    pass


class OcrError(NasmiError):
    pass


class OcrProcessingError(OcrError):
    pass


class OcrLowConfidenceError(OcrError):
    pass


class OcrPreprocessingError(OcrError):
    pass


class OcrEngineError(OcrError):
    pass


class OcrLanguageError(OcrError):
    pass
