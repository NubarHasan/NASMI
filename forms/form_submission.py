from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from core.guards import require
from core.identifiers import (
    generate_form_submission_id,
    is_valid_form_field_id,
    is_valid_form_submission_id,
    is_valid_form_template_id,
)
from core.types import FormFieldId, FormSubmissionId, FormTemplateId
from forms.form_type import SubmissionStatus


@dataclass(frozen=True)
class SubmissionEntry:
    field_id: FormFieldId
    value: Any

    def __post_init__(self) -> None:
        require(is_valid_form_field_id(self.field_id), "field_id has invalid format")
        require(self.value is not None, "value must not be None")


def _require_unique_entries(entries: tuple[SubmissionEntry, ...]) -> None:
    seen: set[str] = set()
    for e in entries:
        require(
            e.field_id not in seen,
            f"duplicate field_id in submission: {e.field_id}",
        )
        seen.add(e.field_id)


@dataclass(frozen=True)
class FormSubmission:
    submission_id: FormSubmissionId
    template_id: FormTemplateId
    version: int
    status: SubmissionStatus
    entries: tuple[SubmissionEntry, ...]
    submitted_at: datetime | None
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        require(
            is_valid_form_submission_id(self.submission_id),
            "submission_id has invalid format",
        )
        require(
            is_valid_form_template_id(self.template_id),
            "template_id has invalid format",
        )
        require(isinstance(self.version, int), "version must be an integer")
        require(self.version >= 1, "version must be >= 1")
        require(
            isinstance(self.status, SubmissionStatus),
            "status must be a SubmissionStatus",
        )
        require(isinstance(self.entries, tuple), "entries must be a tuple")
        require(
            all(isinstance(e, SubmissionEntry) for e in self.entries),
            "all entries must be SubmissionEntry instances",
        )
        require(len(self.entries) > 0, "submission must contain at least one entry")
        _require_unique_entries(self.entries)
        if self.status is SubmissionStatus.DRAFT:
            require(
                self.submitted_at is None,
                "draft submissions must not have submitted_at",
            )
        if self.status is SubmissionStatus.SUBMITTED:
            require(
                self.submitted_at is not None,
                "submitted submissions require submitted_at",
            )
        if self.submitted_at is not None:
            require(
                isinstance(self.submitted_at, datetime),
                "submitted_at must be a datetime",
            )
            require(
                self.submitted_at.tzinfo is not None,
                "submitted_at must be timezone-aware",
            )
        require(isinstance(self.metadata, Mapping), "metadata must be a Mapping")

    @classmethod
    def create_draft(
        cls,
        template_id: FormTemplateId,
        version: int,
        entries: tuple[SubmissionEntry, ...],
        metadata: Mapping[str, Any] | None = None,
        submission_id: FormSubmissionId | None = None,
    ) -> FormSubmission:
        require(
            is_valid_form_template_id(template_id),
            "template_id has invalid format",
        )
        require(isinstance(version, int), "version must be an integer")
        require(version >= 1, "version must be >= 1")
        require(isinstance(entries, tuple), "entries must be a tuple")
        require(
            all(isinstance(e, SubmissionEntry) for e in entries),
            "all entries must be SubmissionEntry instances",
        )
        require(len(entries) > 0, "submission must contain at least one entry")
        _require_unique_entries(entries)

        resolved_id = (
            submission_id
            if submission_id is not None
            else generate_form_submission_id()
        )
        require(
            is_valid_form_submission_id(resolved_id),
            "submission_id has invalid format",
        )

        resolved_metadata = MappingProxyType(
            dict(metadata) if metadata is not None else {}
        )

        return cls(
            submission_id=resolved_id,
            template_id=template_id,
            version=version,
            status=SubmissionStatus.DRAFT,
            entries=entries,
            submitted_at=None,
            metadata=resolved_metadata,
        )

    def submit(
        self,
        submitted_at: datetime | None = None,
    ) -> FormSubmission:
        require(
            self.status is SubmissionStatus.DRAFT,
            "only draft submissions can be submitted",
        )
        resolved_at = submitted_at if submitted_at is not None else datetime.now(UTC)
        require(isinstance(resolved_at, datetime), "submitted_at must be a datetime")
        require(resolved_at.tzinfo is not None, "submitted_at must be timezone-aware")
        return FormSubmission(
            submission_id=self.submission_id,
            template_id=self.template_id,
            version=self.version,
            status=SubmissionStatus.SUBMITTED,
            entries=self.entries,
            submitted_at=resolved_at,
            metadata=self.metadata,
        )

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def get_entry(self, field_id: FormFieldId) -> SubmissionEntry | None:
        require(is_valid_form_field_id(field_id), "field_id has invalid format")
        for e in self.entries:
            if e.field_id == field_id:
                return e
        return None

    def has_entry(self, field_id: FormFieldId) -> bool:
        return self.get_entry(field_id) is not None
