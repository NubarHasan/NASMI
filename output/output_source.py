from enum import StrEnum


class OutputSource(StrEnum):
    PROFILE = "profile"
    KNOWLEDGE_VAULT = "knowledge_vault"
    ACCEPTED_FACTS = "accepted_facts"
    FACTS = "facts"
    EVIDENCE = "evidence"
    PROVENANCE = "provenance"
    CONFLICTS = "conflicts"
    AUDIT_CHAIN = "audit_chain"
    FORM_TEMPLATE = "form_template"
    FORM_SUBMISSION = "form_submission"
    ARCHIVE_DOCUMENTS = "archive_documents"
