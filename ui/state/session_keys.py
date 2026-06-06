from enum import StrEnum


class SessionKeys(StrEnum):
    ACTIVE_USER_ID = "active_user_id"
    ACTIVE_ENTITY_ID = "active_entity_id"
    CURRENT_PAGE = "current_page"

    SELECTED_DOCUMENT_ID = "selected_document_id"
    SELECTED_REVIEW_CASE_ID = "selected_review_case_id"
    SELECTED_CONFLICT_ID = "selected_conflict_id"
    SELECTED_FORM_TEMPLATE_ID = "selected_form_template_id"
    SELECTED_SUBMISSION_ID = "selected_submission_id"
    SELECTED_OUTPUT_ID = "selected_output_id"

    REVIEW_QUEUE = "review_queue"
    DOCUMENT_LIST = "document_list"
    OUTPUT_LIST = "output_list"
    PROFILE_SNAPSHOT = "profile_snapshot"
    AUTOFILL_PREVIEW = "autofill_preview"

    PROCESSING_JOB_ID = "processing_job_id"
    PROCESSING_STATUS = "processing_status"

    ADVISORY_CACHE = "advisory_cache"

    AUDIT_CHAIN = "audit_chain"
    AUDIT_RESULT = "audit_result"
    AUDIT_SELECTED = "audit_selected"
    AUDIT_FILTERS = "audit_filters"

    PENDING_SUBMISSION_ID = "pending_submission_id"
