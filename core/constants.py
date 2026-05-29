from enum import Enum

APP_NAME = "NASMI"
APP_FULL_NAME = "Neural Automated Secure Management of Information"
APP_VERSION = "1.0.0"
PROJECT_AUTHOR = "Nubar Hasan"

DATABASE_FILENAME = "nasmi.db"
AUDIT_FILENAME = "audit.log"
DOCUMENTS_DIRNAME = "documents"
EXPORTS_DIRNAME = "exports"
TEMP_DIRNAME = "temp"
LLM_DIRNAME = "llm"
VECTORS_DIRNAME = "vectors"

MAX_FILE_SIZE_MB = 50
MAX_BATCH_SIZE = 200

DEFAULT_LANGUAGE = "de"
DEFAULT_LLM_CONTEXT_LENGTH = 8192

DEFAULT_HASH_ALGORITHM = "sha256"
AUDIT_CHAIN_VERSION = 1

SQLITE_WAL_MODE = "WAL"
SQLITE_FOREIGN_KEYS = True

SUPPORTED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".webp",
    }
)


class DocumentType(str, Enum):
    PASSPORT = "passport"
    RESIDENCE_PERMIT = "residence_permit"
    PAYSLIP = "payslip"
    EMPLOYMENT_CONTRACT = "employment_contract"
    UNIVERSITY_CERTIFICATE = "university_certificate"
    TAX_DOCUMENT = "tax_document"
    INSURANCE_DOCUMENT = "insurance_document"
    BANK_STATEMENT = "bank_statement"
    INVOICE = "invoice"
    UNKNOWN = "unknown"


class DocumentStatus(str, Enum):
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


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"


class ReviewDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    DEFERRED = "deferred"


class ConflictStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class KnowledgeSourceType(str, Enum):
    DOCUMENT = "document"
    USER_INPUT = "user_input"
    AI_SUGGESTION = "ai_suggestion"


class CoreField(str, Enum):
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    DATE_OF_BIRTH = "date_of_birth"
    PLACE_OF_BIRTH = "place_of_birth"
    NATIONALITY = "nationality"
    GENDER = "gender"
    ADDRESS = "address"
    STREET = "street"
    CITY = "city"
    POSTAL_CODE = "postal_code"
    COUNTRY = "country"
    PHONE = "phone"
    EMAIL = "email"
    IBAN = "iban"
    TAX_NUMBER = "tax_number"
    SOCIAL_SECURITY_NUMBER = "social_security_number"
    PASSPORT_NUMBER = "passport_number"
    RESIDENCE_PERMIT_NUMBER = "residence_permit_number"
    EMPLOYER_NAME = "employer_name"
    JOB_TITLE = "job_title"
    EMPLOYMENT_START = "employment_start"
    EMPLOYMENT_END = "employment_end"
    SALARY = "salary"
    UNIVERSITY_NAME = "university_name"
    DEGREE = "degree"
    FIELD_OF_STUDY = "field_of_study"
    GRADUATION_DATE = "graduation_date"
    INSURANCE_NUMBER = "insurance_number"
    INSURANCE_PROVIDER = "insurance_provider"


class ValidationType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    IBAN = "iban"
    DATE = "date"
    DOCUMENT_DATE = "document_date"
    TAX_NUMBER = "tax_number"
    POSTAL_CODE = "postal_code"
    PASSPORT_NUMBER = "passport_number"
    RESIDENCE_PERMIT_NUMBER = "residence_permit_number"
    INSURANCE_NUMBER = "insurance_number"
    SALARY = "salary"


class AuditEvent(str, Enum):
    DOCUMENT_IMPORTED = "document_imported"
    DOCUMENT_CLASSIFIED = "document_classified"
    DOCUMENT_DEDUPLICATED = "document_deduplicated"
    OCR_COMPLETED = "ocr_completed"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_COMPLETED = "validation_completed"
    CONFLICT_CREATED = "conflict_created"
    CONFLICT_RESOLVED = "conflict_resolved"
    REVIEW_CREATED = "review_created"
    USER_ACCEPTED = "user_accepted"
    USER_REJECTED = "user_rejected"
    USER_EDITED = "user_edited"
    USER_DEFERRED = "user_deferred"
    KNOWLEDGE_CREATED = "knowledge_created"
    KNOWLEDGE_MODIFIED = "knowledge_modified"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    FORM_GENERATED = "form_generated"
    EXPORT_GENERATED = "export_generated"
    PACKAGE_CREATED = "package_created"
    PACKAGE_EXPORTED = "package_exported"


class ExportFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
    XML = "xml"


class ConfidenceLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


CONFIDENCE_THRESHOLDS: dict[ConfidenceLevel, float] = {
    ConfidenceLevel.HIGH: 0.85,
    ConfidenceLevel.MEDIUM: 0.60,
    ConfidenceLevel.LOW: 0.30,
    ConfidenceLevel.NONE: 0.0,
}


class CollectionType(str, Enum):
    IDENTITY = "identity"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    TAX = "tax"
    INSURANCE = "insurance"
    BANKING = "banking"
    HOUSING = "housing"
    LEGAL = "legal"
    FORMS = "forms"
    OTHER = "other"


class PackageStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    EXPORTED = "exported"
