from __future__ import annotations

import re
import uuid

from core.guards import require
from core.types import (
    ArtifactId,
    AuditId,
    ConflictId,
    DocumentId,
    EntityId,
    EvidenceId,
    FactEvidenceId,
    FactId,
    FailureId,
    FormFieldId,
    FormId,
    FormSubmissionId,
    FormTemplateId,
    JobId,
    KnowledgeId,
    PackageId,
    ProfileId,
    ProvenanceId,
    RecordId,
    ReviewId,
    SourceId,
    UserId,
    VaultId,
)

_ID_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z]+-[0-9A-F]{32}$")

_PREFIX_DOCUMENT: str = "DOC"
_PREFIX_REVIEW: str = "REV"
_PREFIX_KNOWLEDGE: str = "KNW"
_PREFIX_PACKAGE: str = "PKG"
_PREFIX_JOB: str = "JOB"
_PREFIX_USER: str = "USR"
_PREFIX_AUDIT: str = "AUD"
_PREFIX_FORM: str = "FRM"
_PREFIX_ENTITY: str = "ENT"
_PREFIX_RECORD: str = "REC"
_PREFIX_CONFLICT: str = "CNF"
_PREFIX_ARTIFACT: str = "ARTF"
_PREFIX_FAILURE: str = "FAIL"
_PREFIX_SOURCE: str = "SRC"
_PREFIX_FACT: str = "FAC"
_PREFIX_EVIDENCE: str = "EVD"
_PREFIX_FACT_EVIDENCE: str = "FEV"
_PREFIX_PROVENANCE: str = "PRV"
_PREFIX_PROFILE: str = "PRF"
_PREFIX_VAULT: str = "VLT"
_PREFIX_FORM_FIELD: str = "FFD"
_PREFIX_FORM_TEMPLATE: str = "FTP"
_PREFIX_FORM_SUBMISSION: str = "FSB"

_KNOWN_PREFIXES: frozenset[str] = frozenset(
    {
        _PREFIX_DOCUMENT,
        _PREFIX_REVIEW,
        _PREFIX_KNOWLEDGE,
        _PREFIX_PACKAGE,
        _PREFIX_JOB,
        _PREFIX_USER,
        _PREFIX_AUDIT,
        _PREFIX_FORM,
        _PREFIX_ENTITY,
        _PREFIX_RECORD,
        _PREFIX_CONFLICT,
        _PREFIX_ARTIFACT,
        _PREFIX_FAILURE,
        _PREFIX_SOURCE,
        _PREFIX_FACT,
        _PREFIX_EVIDENCE,
        _PREFIX_FACT_EVIDENCE,
        _PREFIX_PROVENANCE,
        _PREFIX_PROFILE,
        _PREFIX_VAULT,
        _PREFIX_FORM_FIELD,
        _PREFIX_FORM_TEMPLATE,
        _PREFIX_FORM_SUBMISSION,
    }
)


def generate_id(prefix: str) -> str:
    require(bool(prefix), "prefix must not be empty")
    require(prefix == prefix.upper(), "prefix must be uppercase")
    require(prefix in _KNOWN_PREFIXES, f"unknown prefix: {prefix}")
    body = uuid.uuid4().hex.upper()
    return f"{prefix}-{body}"


def generate_document_id() -> DocumentId:
    return DocumentId(generate_id(_PREFIX_DOCUMENT))


def generate_review_id() -> ReviewId:
    return ReviewId(generate_id(_PREFIX_REVIEW))


def generate_knowledge_id() -> KnowledgeId:
    return KnowledgeId(generate_id(_PREFIX_KNOWLEDGE))


def generate_package_id() -> PackageId:
    return PackageId(generate_id(_PREFIX_PACKAGE))


def generate_job_id() -> JobId:
    return JobId(generate_id(_PREFIX_JOB))


def generate_user_id() -> UserId:
    return UserId(generate_id(_PREFIX_USER))


def generate_audit_id() -> AuditId:
    return AuditId(generate_id(_PREFIX_AUDIT))


def generate_form_id() -> FormId:
    return FormId(generate_id(_PREFIX_FORM))


def generate_entity_id() -> EntityId:
    return EntityId(generate_id(_PREFIX_ENTITY))


def generate_record_id() -> RecordId:
    return RecordId(generate_id(_PREFIX_RECORD))


def generate_conflict_id() -> ConflictId:
    return ConflictId(generate_id(_PREFIX_CONFLICT))


def generate_artifact_id() -> ArtifactId:
    return ArtifactId(generate_id(_PREFIX_ARTIFACT))


def generate_failure_id() -> FailureId:
    return FailureId(generate_id(_PREFIX_FAILURE))


def generate_source_id() -> SourceId:
    return SourceId(generate_id(_PREFIX_SOURCE))


def generate_fact_id() -> FactId:
    return FactId(generate_id(_PREFIX_FACT))


def generate_evidence_id() -> EvidenceId:
    return EvidenceId(generate_id(_PREFIX_EVIDENCE))


def generate_fact_evidence_id() -> FactEvidenceId:
    return FactEvidenceId(generate_id(_PREFIX_FACT_EVIDENCE))


def generate_provenance_id() -> ProvenanceId:
    return ProvenanceId(generate_id(_PREFIX_PROVENANCE))


def generate_profile_id() -> ProfileId:
    return ProfileId(generate_id(_PREFIX_PROFILE))


def generate_vault_id() -> VaultId:
    return VaultId(generate_id(_PREFIX_VAULT))


def generate_form_field_id() -> FormFieldId:
    return FormFieldId(generate_id(_PREFIX_FORM_FIELD))


def generate_form_template_id() -> FormTemplateId:
    return FormTemplateId(generate_id(_PREFIX_FORM_TEMPLATE))


def generate_form_submission_id() -> FormSubmissionId:
    return FormSubmissionId(generate_id(_PREFIX_FORM_SUBMISSION))


def is_valid_id(value: str, prefix: str) -> bool:
    if not isinstance(value, str):
        return False
    if not isinstance(prefix, str):
        return False
    if prefix not in _KNOWN_PREFIXES:
        return False
    if not _ID_PATTERN.match(value):
        return False
    return value.startswith(f"{prefix}-")


def is_valid_document_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_DOCUMENT)


def is_valid_review_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_REVIEW)


def is_valid_knowledge_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_KNOWLEDGE)


def is_valid_package_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_PACKAGE)


def is_valid_job_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_JOB)


def is_valid_user_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_USER)


def is_valid_audit_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_AUDIT)


def is_valid_form_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FORM)


def is_valid_entity_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_ENTITY)


def is_valid_record_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_RECORD)


def is_valid_conflict_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_CONFLICT)


def is_valid_artifact_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_ARTIFACT)


def is_valid_failure_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FAILURE)


def is_valid_source_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_SOURCE)


def is_valid_fact_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FACT)


def is_valid_evidence_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_EVIDENCE)


def is_valid_fact_evidence_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FACT_EVIDENCE)


def is_valid_provenance_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_PROVENANCE)


def is_valid_profile_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_PROFILE)


def is_valid_vault_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_VAULT)


def is_valid_form_field_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FORM_FIELD)


def is_valid_form_template_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FORM_TEMPLATE)


def is_valid_form_submission_id(value: str) -> bool:
    return is_valid_id(value, _PREFIX_FORM_SUBMISSION)


def parse_id(value: str) -> tuple[str, str]:
    require(isinstance(value, str), "value must be a string")
    require(_ID_PATTERN.match(value) is not None, f"invalid id format: {value!r}")
    prefix, body = value.split("-", 1)
    require(prefix in _KNOWN_PREFIXES, f"unknown prefix: {prefix!r}")
    return prefix, body


def get_id_prefix(value: str) -> str:
    prefix, _ = parse_id(value)
    return prefix


def get_id_body(value: str) -> str:
    _, body = parse_id(value)
    return body
