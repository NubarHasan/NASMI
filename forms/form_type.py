from __future__ import annotations

from enum import StrEnum


class FormKind(StrEnum):
    PASSPORT = "passport"
    RESIDENCE_PERMIT = "residence_permit"
    BIRTH_CERTIFICATE = "birth_certificate"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    TAX_FORM = "tax_form"
    BANK_FORM = "bank_form"
    EMPLOYMENT = "employment"
    CUSTOM = "custom"


class FieldType(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    BOOLEAN = "boolean"
    EMAIL = "email"
    PHONE = "phone"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    FILE = "file"
    TEXTAREA = "textarea"


class SubmissionStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
