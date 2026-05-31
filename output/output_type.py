"""
output/output_type.py

Output Kingdom — Type Layer

Every value maps to a locked Kingdom in NASMI:

    Knowledge  → PROFILE_REPORT, KNOWLEDGE_REPORT, FACT_EXPORT,
                 EVIDENCE_REPORT, PROVENANCE_REPORT, CONFLICT_REPORT
    Audit      → AUDIT_REPORT
    Forms      → FORM_SUBMISSION
    Composite  → APPLICATION_PACKAGE

Kingdom: Output
Depends on: nothing
Status: LOCKED
"""

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
