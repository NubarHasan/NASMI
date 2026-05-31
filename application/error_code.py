from enum import StrEnum


class ErrorCode(StrEnum):
    OUTPUT_GENERATOR_NOT_FOUND = "output.generator_not_found"
    OUTPUT_UNSUPPORTED_FORMAT = "output.unsupported_format"
    OUTPUT_GENERATION_FAILED = "output.generation_failed"
    OUTPUT_INVALID_REQUEST = "output.invalid_request"
    OUTPUT_DOCUMENT_NOT_FOUND = "output.document_not_found"

    REVIEW_NOT_FOUND = "review.not_found"
    REVIEW_ALREADY_CLOSED = "review.already_closed"
    REVIEW_INVALID_OUTCOME = "review.invalid_outcome"
    REVIEW_QUEUE_UNAVAILABLE = "review.queue_unavailable"

    KNOWLEDGE_VAULT_UNAVAILABLE = "knowledge.vault_unavailable"
    KNOWLEDGE_FACT_NOT_FOUND = "knowledge.fact_not_found"
    KNOWLEDGE_DUPLICATE_ENTRY = "knowledge.duplicate_entry"

    FORMS_INVALID_SUBMISSION = "forms.invalid_submission"
    FORMS_SCHEMA_NOT_FOUND = "forms.schema_not_found"
    FORMS_ALREADY_SUBMITTED = "forms.already_submitted"

    ARCHIVE_CORRUPTED = "archive.corrupted"
    ARCHIVE_RECORD_NOT_FOUND = "archive.record_not_found"
    ARCHIVE_UNAVAILABLE = "archive.unavailable"

    PIPELINE_JOB_NOT_FOUND = "pipeline.job_not_found"
    PIPELINE_EXECUTION_FAILED = "pipeline.execution_failed"
    PIPELINE_INVALID_STATE = "pipeline.invalid_state"
