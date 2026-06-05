from enum import StrEnum


class OutputType(StrEnum):
    PROFILE_REPORT = "profile_report"
    KNOWLEDGE_REPORT = "knowledge_report"
    FACT_EXPORT = "fact_export"
    EVIDENCE_REPORT = "evidence_report"
    PROVENANCE_REPORT = "provenance_report"
    CONFLICT_REPORT = "conflict_report"
    AUDIT_REPORT = "audit_report"
    FORM_SUBMISSION = "form_submission"
    APPLICATION_PACKAGE = "application_package"
