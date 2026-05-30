from enum import StrEnum

APP_NAME = "NASMI"
APP_FULL_NAME = "Neural Automated Secure Management of Information"
APP_VERSION = "1.0.0"
PROJECT_AUTHOR = "Nubar Hasan"

API_VERSION = "v1"
SCHEMA_VERSION = "1.0"
KNOWLEDGE_VERSION = "1"
PACKAGE_VERSION = "1"

DATABASE_FILENAME = "nasmi.db"
DATABASE_TIMEOUT = 30

HASH_ALGORITHM = "sha256"
AUDIT_CHAIN_VERSION = 1

UUID_LENGTH = 36
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_BATCH_SIZE = 100
MAX_FILENAME_LENGTH = 255
DEFAULT_CHUNK_SIZE = 8192

DEFAULT_LANGUAGE = "deu"
DEFAULT_ENCODING = "utf-8"
DEFAULT_TIMEZONE = "UTC"
DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

DEFAULT_LLM_CONTEXT_LENGTH = 8192
DEFAULT_LLM_THREADS = 4
DEFAULT_LLM_TEMPERATURE = 0.1

SUPPORTED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".tif",
        ".bmp",
        ".webp",
        ".docx",
        ".xlsx",
        ".csv",
        ".json",
        ".xml",
    }
)

SUPPORTED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/bmp",
        "image/webp",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "application/json",
        "application/xml",
    }
)

CONFIDENCE_THRESHOLDS: dict[str, float] = {
    "ocr": 0.80,
    "extraction": 0.75,
    "validation": 0.90,
    "autofill": 0.85,
}


class DocumentType(StrEnum):
    PASSPORT = "passport"
    RESIDENCE_PERMIT = "residence_permit"
    RESIDENCE_DECISION = "residence_decision"
    RESIDENCE_REGISTRATION = "residence_registration"
    NATIONAL_ID = "national_id"
    DRIVING_LICENSE = "driving_license"
    VEHICLE_DOCUMENT = "vehicle_document"
    TAX_DOCUMENT = "tax_document"
    TAX_ASSESSMENT = "tax_assessment"
    INSURANCE_DOCUMENT = "insurance_document"
    INSURANCE_POLICY = "insurance_policy"
    EMPLOYMENT_CONTRACT = "employment_contract"
    EMPLOYMENT_REFERENCE = "employment_reference"
    PAYSLIP = "payslip"
    BANK_STATEMENT = "bank_statement"
    BANK_CARD = "bank_card"
    UTILITY_BILL = "utility_bill"
    RENTAL_CONTRACT = "rental_contract"
    UNIVERSITY_CERTIFICATE = "university_certificate"
    DEGREE_CERTIFICATE = "degree_certificate"
    LANGUAGE_CERTIFICATE = "language_certificate"
    TRANSCRIPT = "transcript"
    CV = "cv"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    BIRTH_CERTIFICATE = "birth_certificate"
    MEDICAL_DOCUMENT = "medical_document"
    COURT_DOCUMENT = "court_document"
    INVOICE = "invoice"
    FORM = "form"
    APPLICATION = "application"
    OTHER = "other"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    IMPORTED = "imported"
    CLASSIFIED = "classified"
    OCR_COMPLETED = "ocr_completed"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_COMPLETED = "validation_completed"
    REVIEW_PENDING = "review_pending"
    REVIEW_COMPLETED = "review_completed"
    KNOWLEDGE_COMMITTED = "knowledge_committed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    ESCALATED = "escalated"


class ReviewDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    DEFERRED = "deferred"


class ConflictStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    IGNORED = "ignored"


class PackageStatus(StrEnum):
    DRAFT = "draft"
    BUILDING = "building"
    READY = "ready"
    EXPORTED = "exported"
    ARCHIVED = "archived"
    ERROR = "error"


class JobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class KnowledgeStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class KnowledgeSourceType(StrEnum):
    DOCUMENT = "document"
    USER_INPUT = "user_input"
    AI_SUGGESTION = "ai_suggestion"
    IMPORT = "import"


class ConfidenceLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class CollectionType(StrEnum):
    IDENTITY = "identity"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    TAX = "tax"
    INSURANCE = "insurance"
    BANKING = "banking"
    HOUSING = "housing"
    LEGAL = "legal"
    IMMIGRATION = "immigration"
    UNIVERSITY = "university"
    FORMS = "forms"
    OTHER = "other"


class ExportFormat(StrEnum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
    XML = "xml"


class AIModelRole(StrEnum):
    OCR_ASSISTANT = "ocr_assistant"
    CLASSIFICATION_ASSISTANT = "classification_assistant"
    EXTRACTION_ASSISTANT = "extraction_assistant"
    KNOWLEDGE_ASSISTANT = "knowledge_assistant"
    FORM_ASSISTANT = "form_assistant"
    ARCHIVE_ASSISTANT = "archive_assistant"


class ValidationType(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    IBAN = "iban"
    DATE = "date"
    POSTAL_CODE = "postal_code"
    TAX_NUMBER = "tax_number"
    PASSPORT_NUMBER = "passport_number"
    RESIDENCE_PERMIT_NUMBER = "residence_permit_number"
    INSURANCE_NUMBER = "insurance_number"
    BANK_ACCOUNT = "bank_account"


class SystemComponent(StrEnum):
    CORE = "core"
    ARCHIVE = "archive"
    OCR = "ocr"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    REVIEW = "review"
    KNOWLEDGE = "knowledge"
    FORMS = "forms"
    PACKAGES = "packages"
    AUDIT = "audit"
    AI = "ai"
    STORAGE = "storage"
    DATABASE = "database"
    API = "api"
    UI = "ui"


class EntityType(StrEnum):
    DOCUMENT = "document"
    FIELD = "field"
    REVIEW = "review"
    CONFLICT = "conflict"
    KNOWLEDGE = "knowledge"
    PACKAGE = "package"
    FORM = "form"
    AUDIT_EVENT = "audit_event"
    JOB = "job"


class SeverityLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(StrEnum):
    DOCUMENT_IMPORTED = "document_imported"
    DOCUMENT_DEDUPLICATED = "document_deduplicated"
    OCR_COMPLETED = "ocr_completed"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_COMPLETED = "validation_completed"
    CONFLICT_CREATED = "conflict_created"
    CONFLICT_RESOLVED = "conflict_resolved"
    REVIEW_CREATED = "review_created"
    REVIEW_ACCEPTED = "review_accepted"
    REVIEW_REJECTED = "review_rejected"
    REVIEW_EDITED = "review_edited"
    USER_ACCEPTED = "user_accepted"
    USER_REJECTED = "user_rejected"
    USER_EDITED = "user_edited"
    USER_DEFERRED = "user_deferred"
    KNOWLEDGE_CREATED = "knowledge_created"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    KNOWLEDGE_SUPERSEDED = "knowledge_superseded"
    FORM_GENERATED = "form_generated"
    PACKAGE_CREATED = "package_created"
    PACKAGE_EXPORTED = "package_exported"
    EXPORT_GENERATED = "export_generated"
