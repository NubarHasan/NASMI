from __future__ import annotations

import streamlit as st

from forms.autofill_preview import PreviewFieldStatus
from forms.form_submission import FormSubmission
from forms.form_type import FieldType, SubmissionStatus
from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.forms_vm import FormsVM, SubmitResult


def _render_template_list(vm: FormsVM) -> None:
    templates = vm.list_templates()

    if not templates:
        st.info("No form templates available.")
        return

    for tmpl in templates:
        col_name, col_kind, col_fields, col_ver, col_action = st.columns(
            [3, 2, 1, 1, 2]
        )
        with col_name:
            st.write(tmpl.name)
        with col_kind:
            st.write(vm.kind_label(tmpl.form_kind))
        with col_fields:
            st.write(f"{tmpl.field_count} fields")
        with col_ver:
            st.write(f"v{tmpl.version}")
        with col_action:
            if st.button("Fill", key=f"fill_{tmpl.template_id}"):
                sm.set(SessionKeys.SELECTED_FORM_TEMPLATE_ID, tmpl.template_id)
                sm.reset(SessionKeys.SELECTED_SUBMISSION_ID)
                sm.reset(SessionKeys.AUTOFILL_PREVIEW)
                st.rerun()


def _render_form_fill(vm: FormsVM, template_id: str) -> None:
    template = vm.get_template(template_id)

    if template is None:
        st.warning("Template not found.")
        sm.reset(SessionKeys.SELECTED_FORM_TEMPLATE_ID)
        return

    if st.button("← Back"):
        sm.reset(SessionKeys.SELECTED_FORM_TEMPLATE_ID)
        sm.reset(SessionKeys.AUTOFILL_PREVIEW)
        sm.reset(SessionKeys.SELECTED_SUBMISSION_ID)
        st.rerun()

    st.subheader(template.name)
    st.caption(f"{vm.kind_label(template.form_kind)}  ·  v{template.version}")

    col_auto, _ = st.columns([2, 8])
    with col_auto:
        if st.button("⚡ Autofill", key="autofill_btn"):
            autofill_result = vm.autofill(template_id)
            if autofill_result.success:
                sm.set(SessionKeys.AUTOFILL_PREVIEW, autofill_result.preview)
            else:
                st.error(autofill_result.error)

    st.divider()

    autofill_preview = sm.get(SessionKeys.AUTOFILL_PREVIEW)
    field_values: dict[str, str] = {}

    for field in template.fields:
        suggested = None
        if autofill_preview is not None:
            for pf in autofill_preview.preview_fields:
                if pf.field_name == field.field_name:
                    if pf.status is PreviewFieldStatus.FILLED:
                        suggested = (
                            str(pf.suggested) if pf.suggested is not None else ""
                        )
                    break

        label = f"{field.label} {'*' if field.is_required else ''}"
        default = suggested or (str(field.default_value) if field.has_default else "")

        if field.field_type is FieldType.TEXTAREA:
            value = st.text_area(label, value=default, key=f"field_{field.field_name}")
        elif field.field_type is FieldType.BOOLEAN:
            value = str(
                st.checkbox(label, value=bool(default), key=f"field_{field.field_name}")
            )
        elif field.field_type is FieldType.INTEGER:
            value = str(
                st.number_input(
                    label,
                    value=int(default) if default else 0,
                    step=1,
                    key=f"field_{field.field_name}",
                )
            )
        elif field.field_type is FieldType.DECIMAL:
            value = str(
                st.number_input(
                    label,
                    value=float(default) if default else 0.0,
                    step=0.01,
                    key=f"field_{field.field_name}",
                )
            )
        else:
            value = st.text_input(label, value=default, key=f"field_{field.field_name}")

        field_values[field.field_name] = value

    st.divider()

    col_draft, col_submit, _ = st.columns([2, 2, 6])

    with col_draft:
        if st.button("💾 Save Draft", type="primary"):
            draft_result: SubmitResult = vm.build_draft(template_id, field_values)
            saved: FormSubmission | None = draft_result.submission
            if draft_result.success and saved is not None:
                sm.set(SessionKeys.SELECTED_SUBMISSION_ID, saved.submission_id)
                sm.set(SessionKeys.PENDING_SUBMISSION_ID, saved.submission_id)
                st.session_state["_pending_submission_obj"] = saved
                st.success("Draft saved.")
                st.rerun()
            else:
                st.error(draft_result.error)

    with col_submit:
        pending: FormSubmission | None = st.session_state.get("_pending_submission_obj")
        if (
            pending is not None
            and pending.status is SubmissionStatus.DRAFT
            and st.button("✅ Submit")
        ):
            submit_result: SubmitResult = vm.submit(pending)
            submitted: FormSubmission | None = submit_result.submission
            if submit_result.success and submitted is not None:
                st.session_state["_pending_submission_obj"] = submitted
                st.success("Submitted successfully.")
                st.rerun()
            else:
                st.error(submit_result.error)

    pending_obj: FormSubmission | None = st.session_state.get("_pending_submission_obj")
    if pending_obj is not None:
        st.caption(f"Status: {vm.status_badge(pending_obj.status)}")


def render() -> None:
    st.title("Forms")

    vm = FormsVM()
    selected_template_id: str | None = sm.get(SessionKeys.SELECTED_FORM_TEMPLATE_ID)

    if selected_template_id:
        _render_form_fill(vm, selected_template_id)
    else:
        st.subheader("Available Templates")
        _render_template_list(vm)
