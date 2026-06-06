from __future__ import annotations

from core.guards import require
from core.identifiers import is_valid_form_submission_id, is_valid_form_template_id
from core.types import FormSubmissionId, FormTemplateId
from forms.form_submission import FormSubmission
from forms.form_type import SubmissionStatus


class InMemoryFormSubmissionRepository:
    """
    Infrastructure Implementation.

    Implements FormSubmissionRepository Protocol using an in-memory dict.
    Intended for testing and early development only.

    Storage key: submission_id (str)
    """

    def __init__(self) -> None:
        self._store: dict[FormSubmissionId, FormSubmission] = {}

    def get_by_id(self, submission_id: FormSubmissionId) -> FormSubmission | None:
        require(
            is_valid_form_submission_id(submission_id),
            "submission_id has invalid format",
        )
        return self._store.get(submission_id)

    def get_by_template_id(
        self,
        template_id: FormTemplateId,
    ) -> tuple[FormSubmission, ...]:
        require(
            is_valid_form_template_id(template_id), "template_id has invalid format"
        )
        return tuple(s for s in self._store.values() if s.template_id == template_id)

    def get_by_status(
        self,
        status: SubmissionStatus,
    ) -> tuple[FormSubmission, ...]:
        require(
            isinstance(status, SubmissionStatus), "status must be a SubmissionStatus"
        )
        return tuple(s for s in self._store.values() if s.status is status)

    def save(self, submission: FormSubmission) -> None:
        require(
            isinstance(submission, FormSubmission),
            "submission must be a FormSubmission",
        )
        self._store[submission.submission_id] = submission

    def exists(self, submission_id: FormSubmissionId) -> bool:
        require(
            is_valid_form_submission_id(submission_id),
            "submission_id has invalid format",
        )
        return submission_id in self._store
