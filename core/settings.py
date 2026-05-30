from dataclasses import dataclass, field

from core.constants import (
    API_VERSION,
    APP_FULL_NAME,
    APP_NAME,
    APP_VERSION,
    AUDIT_CHAIN_VERSION,
    CONFIDENCE_THRESHOLDS,
    DATABASE_FILENAME,
    DATABASE_TIMEOUT,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_ENCODING,
    DEFAULT_LANGUAGE,
    DEFAULT_LLM_CONTEXT_LENGTH,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_LLM_THREADS,
    DEFAULT_TIMEZONE,
    HASH_ALGORITHM,
    MAX_BATCH_SIZE,
    MAX_FILE_SIZE,
    PROJECT_AUTHOR,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_MIME_TYPES,
)

_VALID_HASH_ALGORITHMS = {"sha256", "sha384", "sha512"}
_VALID_JOURNAL_MODES = {"WAL", "DELETE", "TRUNCATE", "PERSIST", "MEMORY", "OFF"}
_VALID_SYNCHRONOUS = {"OFF", "NORMAL", "FULL", "EXTRA"}


@dataclass(frozen=True)
class AppSettings:
    name: str = APP_NAME
    full_name: str = APP_FULL_NAME
    version: str = APP_VERSION
    author: str = PROJECT_AUTHOR
    api_version: str = API_VERSION
    settings_version: str = "1.0"
    debug: bool = False


@dataclass(frozen=True)
class DatabaseSettings:
    filename: str = DATABASE_FILENAME
    timeout: int = DATABASE_TIMEOUT
    echo: bool = False
    journal_mode: str = "WAL"
    synchronous: str = "FULL"
    foreign_keys: bool = True
    busy_timeout_ms: int = 30_000

    def __post_init__(self) -> None:
        if self.busy_timeout_ms < 0:
            raise ValueError(
                f"busy_timeout_ms must be >= 0, got {self.busy_timeout_ms}"
            )
        if self.journal_mode not in _VALID_JOURNAL_MODES:
            raise ValueError(f"Invalid journal_mode: {self.journal_mode!r}")
        if self.synchronous not in _VALID_SYNCHRONOUS:
            raise ValueError(f"Invalid synchronous: {self.synchronous!r}")


@dataclass(frozen=True)
class StorageSettings:
    max_file_size: int = MAX_FILE_SIZE
    max_batch_size: int = MAX_BATCH_SIZE
    chunk_size: int = DEFAULT_CHUNK_SIZE
    encoding: str = DEFAULT_ENCODING
    allowed_extensions: frozenset[str] = SUPPORTED_EXTENSIONS
    allowed_mime_types: frozenset[str] = SUPPORTED_MIME_TYPES
    deduplication_enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_file_size < 1:
            raise ValueError(f"max_file_size must be >= 1, got {self.max_file_size}")
        if self.chunk_size < 512:
            raise ValueError(f"chunk_size must be >= 512, got {self.chunk_size}")


@dataclass(frozen=True)
class ArchiveSettings:
    enable_deduplication: bool = True
    preserve_original_files: bool = True
    calculate_file_hashes: bool = True
    verify_existing_hashes: bool = True


@dataclass(frozen=True)
class OCRSettings:
    language: str = DEFAULT_LANGUAGE
    min_confidence: float = CONFIDENCE_THRESHOLDS["ocr"]
    enable_gpu: bool = False
    max_image_size: int = 4096
    dpi: int = 300
    deskew_enabled: bool = True
    orientation_detection: bool = True
    preprocessing_enabled: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"OCR min_confidence must be in [0.0, 1.0], got {self.min_confidence}"
            )
        if self.dpi < 72:
            raise ValueError(f"OCR dpi must be >= 72, got {self.dpi}")
        if self.max_image_size < 256:
            raise ValueError(
                f"OCR max_image_size must be >= 256, got {self.max_image_size}"
            )


@dataclass(frozen=True)
class ExtractionSettings:
    min_confidence: float = CONFIDENCE_THRESHOLDS["extraction"]
    autofill_min: float = CONFIDENCE_THRESHOLDS["autofill"]
    allow_partial: bool = True
    preserve_raw_text: bool = True
    store_confidence_scores: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"Extraction min_confidence must be in [0.0, 1.0], got {self.min_confidence}"
            )
        if not 0.0 <= self.autofill_min <= 1.0:
            raise ValueError(
                f"Extraction autofill_min must be in [0.0, 1.0], got {self.autofill_min}"
            )


@dataclass(frozen=True)
class ValidationSettings:
    min_confidence: float = CONFIDENCE_THRESHOLDS["validation"]
    strict_mode: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"Validation min_confidence must be in [0.0, 1.0], got {self.min_confidence}"
            )


@dataclass(frozen=True)
class ReviewSettings:
    require_human_confirmation: bool = True
    allow_bulk_accept: bool = False
    allow_bulk_reject: bool = False
    auto_close_resolved_conflicts: bool = True
    require_source_visibility: bool = True
    require_reason_for_rejection: bool = True


@dataclass(frozen=True)
class KnowledgeSettings:
    keep_history: bool = True
    enable_versioning: bool = True
    allow_superseded_records: bool = True
    enable_provenance_tracking: bool = True
    enable_conflict_tracking: bool = True


@dataclass(frozen=True)
class FormsSettings:
    enable_autofill: bool = True
    require_review_before_fill: bool = True
    allow_partial_autofill: bool = True
    store_fill_history: bool = True


@dataclass(frozen=True)
class PackageSettings:
    auto_detect_missing_documents: bool = True
    include_audit_manifest: bool = True
    include_source_documents: bool = True
    include_metadata: bool = True


@dataclass(frozen=True)
class ExportSettings:
    include_audit_manifest: bool = True
    include_metadata: bool = True


@dataclass(frozen=True)
class AISettings:
    context_length: int = DEFAULT_LLM_CONTEXT_LENGTH
    threads: int = DEFAULT_LLM_THREADS
    temperature: float = DEFAULT_LLM_TEMPERATURE
    default_model: str = ""
    allow_downloads: bool = True
    offline_only: bool = True
    allow_network_access: bool = False
    max_loaded_models: int = 1
    enable_gpu: bool = False
    allow_database_writes: bool = False
    allow_decision_override: bool = False
    require_user_confirmation: bool = True

    def __post_init__(self) -> None:
        if self.threads < 1:
            raise ValueError(f"AI threads must be >= 1, got {self.threads}")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"AI temperature must be in [0.0, 2.0], got {self.temperature}"
            )
        if self.context_length < 512:
            raise ValueError(
                f"AI context_length must be >= 512, got {self.context_length}"
            )
        if self.max_loaded_models < 1:
            raise ValueError(
                f"AI max_loaded_models must be >= 1, got {self.max_loaded_models}"
            )
        if self.offline_only and self.allow_network_access:
            raise ValueError(
                "Conflict: ai.offline_only=True cannot coexist with ai.allow_network_access=True"
            )
        if self.allow_database_writes:
            raise ValueError(
                "AI layer must never write to the database directly (allow_database_writes must be False)"
            )
        if self.allow_decision_override:
            raise ValueError(
                "AI layer must never override user decisions (allow_decision_override must be False)"
            )


@dataclass(frozen=True)
class PipelineSettings:
    max_workers: int = 4
    queue_size: int = 1000
    retry_count: int = 3
    retry_delay_seconds: int = 5
    enable_parallel_processing: bool = True

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
        if self.queue_size < 1:
            raise ValueError(f"queue_size must be >= 1, got {self.queue_size}")
        if self.retry_count < 0:
            raise ValueError(f"retry_count must be >= 0, got {self.retry_count}")
        if self.retry_delay_seconds < 0:
            raise ValueError(
                f"retry_delay_seconds must be >= 0, got {self.retry_delay_seconds}"
            )


@dataclass(frozen=True)
class AuditSettings:
    enabled: bool = True
    chain_version: int = AUDIT_CHAIN_VERSION
    algorithm: str = HASH_ALGORITHM
    max_log_size: int = 10 * 1024 * 1024
    backup_count: int = 5
    verify_chain_on_startup: bool = True
    store_event_payloads: bool = True

    def __post_init__(self) -> None:
        if self.algorithm not in _VALID_HASH_ALGORITHMS:
            raise ValueError(
                f"Invalid audit algorithm: {self.algorithm!r}. Must be one of {_VALID_HASH_ALGORITHMS}"
            )


@dataclass(frozen=True)
class SecuritySettings:
    algorithm: str = HASH_ALGORITHM
    hmac_enabled: bool = True
    integrity_check: bool = True
    tamper_detection: bool = True
    verify_file_hashes: bool = True
    verify_record_integrity: bool = True

    def __post_init__(self) -> None:
        if self.algorithm not in _VALID_HASH_ALGORITHMS:
            raise ValueError(
                f"Invalid security algorithm: {self.algorithm!r}. Must be one of {_VALID_HASH_ALGORITHMS}"
            )


@dataclass(frozen=True)
class LocalizationSettings:
    language: str = DEFAULT_LANGUAGE
    timezone: str = DEFAULT_TIMEZONE
    encoding: str = DEFAULT_ENCODING


@dataclass(frozen=True)
class HealthSettings:
    verify_database: bool = True
    verify_storage: bool = True
    verify_models: bool = True
    verify_database_integrity: bool = True
    verify_audit_chain: bool = True
    verify_disk_space: bool = True


@dataclass(frozen=True)
class StartupSettings:
    create_missing_directories: bool = True
    fail_fast: bool = True
    show_banner: bool = True


@dataclass(frozen=True)
class NasmiSettings:
    app: AppSettings = field(default_factory=AppSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    archive: ArchiveSettings = field(default_factory=ArchiveSettings)
    ocr: OCRSettings = field(default_factory=OCRSettings)
    extraction: ExtractionSettings = field(default_factory=ExtractionSettings)
    validation: ValidationSettings = field(default_factory=ValidationSettings)
    review: ReviewSettings = field(default_factory=ReviewSettings)
    knowledge: KnowledgeSettings = field(default_factory=KnowledgeSettings)
    forms: FormsSettings = field(default_factory=FormsSettings)
    packages: PackageSettings = field(default_factory=PackageSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    ai: AISettings = field(default_factory=AISettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)
    audit: AuditSettings = field(default_factory=AuditSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    localization: LocalizationSettings = field(default_factory=LocalizationSettings)
    health: HealthSettings = field(default_factory=HealthSettings)
    startup: StartupSettings = field(default_factory=StartupSettings)

    def __post_init__(self) -> None:
        if self.health.verify_audit_chain and not self.audit.enabled:
            raise ValueError(
                "Conflict: health.verify_audit_chain=True requires audit.enabled=True"
            )
        if self.storage.deduplication_enabled and not self.archive.enable_deduplication:
            raise ValueError(
                "Conflict: storage.deduplication_enabled=True requires archive.enable_deduplication=True"
            )
        if self.security.verify_file_hashes and not self.archive.calculate_file_hashes:
            raise ValueError(
                "Conflict: security.verify_file_hashes=True requires archive.calculate_file_hashes=True"
            )
        if (
            self.forms.require_review_before_fill
            and not self.review.require_human_confirmation
        ):
            raise ValueError(
                "Conflict: forms.require_review_before_fill=True requires review.require_human_confirmation=True"
            )
        if self.audit.algorithm != self.security.algorithm:
            raise ValueError(
                f"Conflict: audit.algorithm={self.audit.algorithm!r} "
                f"must match security.algorithm={self.security.algorithm!r}"
            )


settings = NasmiSettings()
