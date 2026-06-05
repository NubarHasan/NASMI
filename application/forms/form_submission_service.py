from __future__ import annotations

from application.ports.form_submission_repository import FormSubmissionRepository
from core.guards import require
from core.types import FormSubmissionId
from forms.autofill_preview import AutofillPreview
from forms.form_submission import FormSubmission
from forms.form_template import FormTemplate
from forms.form_type import SubmissionStatus


class DraftNotFoundError(Exception):
    def __init__(self, submission_id: FormSubmissionId) -> None:
        super().__init__(f"FormSubmission not found: {submission_id!r}")
        self.submission_id = submission_id


class InvalidSubmissionStatusError(Exception):
    def __init__(
        self,
        submission_id: FormSubmissionId,
        current_status: SubmissionStatus,
    ) -> None:
        super().__init__(
            f"FormSubmission {submission_id!r} cannot be submitted "
            f"from status {current_status.value!r}."
        )
        self.submission_id = submission_id
        self.current_status = current_status


class FormSubmissionService:
    """
    Application Service.

    Responsibility: manage the lifecycle of FormSubmission.

      Phase 1 — build_draft():
        AutofillPreview + FormTemplate → FormSubmission(DRAFT) → save → return draft

      Phase 2 — submit():
        load DRAFT → submit() → save SUBMITTED → return submission

    Does NOT:
      - implement autofill logic
      - implement mapping logic
      - interact with UI
      - decide when to submit (that is the caller's responsibility)
    """

    def __init__(
        self,
        submission_repository: FormSubmissionRepository,
    ) -> None:
        require(
            submission_repository is not None,
            "submission_repository is required",
        )
        self._submission_repository = submission_repository

    def build_draft(
        self,
        preview: AutofillPreview,
        template: FormTemplate,
    ) -> FormSubmission:
        """
        Build a DRAFT FormSubmission from a confirmed AutofillPreview and persist it.

        The caller is responsible for ensuring the user has reviewed the preview
        before invoking this method (Human-in-the-Loop).

        Returns:
            FormSubmission with status DRAFT.
        """
        require(
            isinstance(preview, AutofillPreview), "preview must be an AutofillPreview"
        )
        require(isinstance(template, FormTemplate), "template must be a FormTemplate")

        draft = preview.build_draft(template)
        self._submission_repository.save(draft)
        return draft

    def submit(
        self,
        submission_id: FormSubmissionId,
    ) -> FormSubmission:
        """
        Transition a DRAFT FormSubmission to SUBMITTED and persist it.

        Raises:
            DraftNotFoundError:            if no submission exists for submission_id.
            InvalidSubmissionStatusError:  if the submission is not in DRAFT status.

        Returns:
            FormSubmission with status SUBMITTED.
        """
        draft = self._submission_repository.get_by_id(submission_id)
        if draft is None:
            raise DraftNotFoundError(submission_id)

        if draft.status is not SubmissionStatus.DRAFT:
            raise InvalidSubmissionStatusError(submission_id, draft.status)

        submitted = draft.submit()
        self._submission_repository.save(submitted)
        return submitted
