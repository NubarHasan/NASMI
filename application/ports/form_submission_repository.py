from __future__ import annotations

from typing import Protocol

from core.types import FormSubmissionId, FormTemplateId
from forms.form_submission import FormSubmission
from forms.form_type import SubmissionStatus


class FormSubmissionRepository(Protocol):

    def get_by_id(self, submission_id: FormSubmissionId) -> FormSubmission | None:
        """Return FormSubmission by ID, or None if not found."""
        ...

    def get_by_template_id(
        self,
        template_id: FormTemplateId,
    ) -> tuple[FormSubmission, ...]:
        """Return all submissions for a given template."""
        ...

    def get_by_status(
        self,
        status: SubmissionStatus,
    ) -> tuple[FormSubmission, ...]:
        """Return all submissions with a given status."""
        ...

    def save(self, submission: FormSubmission) -> None:
        """Persist a new or updated FormSubmission."""
        ...

    def exists(self, submission_id: FormSubmissionId) -> bool:
        """Return True if a submission with this ID exists."""
        ...
