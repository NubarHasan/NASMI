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


class InitializationError(CoreError):
    pass


class StartupError(CoreError):
    pass


class ArchiveError(NasmiError):
    pass


class DuplicateDocumentError(ArchiveError):
    pass


class UnsupportedFileTypeError(ArchiveError):
    pass


class FileSizeLimitError(ArchiveError):
    pass


class FileHashMismatchError(ArchiveError):
    pass


class OCRError(NasmiError):
    pass


class OCRLowConfidenceError(OCRError):
    pass


class OCRPreprocessingError(OCRError):
    pass


class OCREngineError(OCRError):
    pass


class OCRLanguageError(OCRError):
    pass


class ExtractionError(NasmiError):
    pass


class FieldExtractionError(ExtractionError):
    pass


class ExtractionLowConfidenceError(ExtractionError):
    pass


class ValidationError(NasmiError):
    pass


class FieldValidationError(ValidationError):
    pass


class ValidationRuleError(ValidationError):
    pass


class ReviewError(NasmiError):
    pass


class ConflictError(ReviewError):
    pass


class ReviewAlreadyClosedError(ReviewError):
    pass


class ReviewDecisionError(ReviewError):
    pass


class ReviewConflictResolutionError(ReviewError):
    pass


class KnowledgeError(NasmiError):
    pass


class KnowledgeNotFoundError(KnowledgeError):
    pass


class ProvenanceError(KnowledgeError):
    pass


class KnowledgeConflictError(KnowledgeError):
    pass


class KnowledgeVersionError(KnowledgeError):
    pass


class FormsError(NasmiError):
    pass


class AutofillError(FormsError):
    pass


class FormGenerationError(FormsError):
    pass


class FormFieldMissingError(FormsError):
    pass


class TemplateNotFoundError(FormsError):
    pass


class PackageError(NasmiError):
    pass


class MissingDocumentError(PackageError):
    pass


class PackageBuildError(PackageError):
    pass


class PackageExportError(PackageError):
    pass


class PackageValidationError(PackageError):
    pass


class AuditError(NasmiError):
    pass


class ChainIntegrityError(AuditError):
    pass


class AuditEventError(AuditError):
    pass


class AIError(NasmiError):
    pass


class ModelNotFoundError(AIError):
    pass


class ModelLoadError(AIError):
    pass


class AIInferenceError(AIError):
    pass


class AIBoundaryViolationError(AIError):
    pass


class StorageError(NasmiError):
    pass


class StorageFileNotFoundError(StorageError):
    pass


class FileWriteError(StorageError):
    pass


class DirectoryError(StorageError):
    pass


class SecurityError(NasmiError):
    pass


class IntegrityViolationError(SecurityError):
    pass


class HMACVerificationError(SecurityError):
    pass


class SignatureVerificationError(SecurityError):
    pass


class PermissionDeniedError(SecurityError):
    pass


class HealthError(NasmiError):
    pass


class HealthCheckFailedError(HealthError):
    pass


class PipelineError(NasmiError):
    pass


class JobError(PipelineError):
    pass


class JobTimeoutError(PipelineError):
    pass


class JobCancelledError(PipelineError):
    pass


class QueueOverflowError(PipelineError):
    pass


class PipelineAbortError(PipelineError):
    pass


class DatabaseError(NasmiError):
    pass


class DatabaseConnectionError(DatabaseError):
    pass


class RecordNotFoundError(DatabaseError):
    pass


class RecordIntegrityError(DatabaseError):
    pass


class DuplicateRecordError(DatabaseError):
    pass


class TransactionError(DatabaseError):
    pass


class MigrationError(DatabaseError):
    pass
