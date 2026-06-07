from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.forms_vm import DynamicFormTemplate, FormsVM


def _save_uploaded_template(uploaded_file: Any) -> str:
    target_dir = Path("data/forms/uploads")
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = uploaded_file.name.replace(" ", "_")
    target_path = target_dir / safe_name
    target_path.write_bytes(uploaded_file.getbuffer())
    return str(target_path)


def _get_active_entity_id() -> str | None:
    value = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
    return str(value) if value is not None else None


def _get_selected_template_id() -> str | None:
    value = sm.get(SessionKeys.SELECTED_FORM_TEMPLATE_ID)
    return str(value) if value is not None else None


def _set_selected_template_id(template_id: str | None) -> None:
    if template_id:
        sm.set(SessionKeys.SELECTED_FORM_TEMPLATE_ID, template_id)
    else:
        sm.reset(SessionKeys.SELECTED_FORM_TEMPLATE_ID)


def _render_create_template(vm: FormsVM) -> None:
    st.subheader("Upload Form")

    st.info(
        "Upload a fillable Anmeldung PDF. NASMI will fill the known fields automatically from the Trusted Profile."
    )

    with st.form("create_dynamic_form_template", clear_on_submit=True):
        name = st.text_input("Form name", value="Anmeldung")
        description = st.text_area("Description", placeholder="Optional")
        uploaded_pdf = st.file_uploader("Upload blank fillable PDF", type=["pdf"])

        submitted = st.form_submit_button("Create Form", type="primary")

    if submitted:
        try:
            if uploaded_pdf is None:
                st.error("Please upload a PDF file.")
                return

            source_file_path = _save_uploaded_template(uploaded_pdf)

            template = vm.create_template(
                name=name,
                description=description,
                form_type="anmeldung",
                source_file_path=source_file_path,
                metadata={"uploaded_file_name": uploaded_pdf.name},
            )

            _set_selected_template_id(template.template_id)
            st.success("Form created.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _render_templates_list(vm: FormsVM) -> None:
    st.subheader("Saved Forms")

    templates = vm.list_templates()

    if not templates:
        st.info("No forms yet. Upload an Anmeldung PDF first.")
        return

    for template in templates:
        smart_fields = vm.list_smart_visible_fields(template.template_id)
        mapped_count = len(
            [item for item in smart_fields if item.field.profile_field_name]
        )

        with st.container(border=True):
            col_info, col_status, col_actions = st.columns([5, 3, 2])

            with col_info:
                st.markdown(f"**{template.name}**")
                st.caption(template.description or "No description")
                st.caption(f"PDF: {template.source_file_path or 'No PDF'}")

            with col_status:
                st.write(f"Useful fields: {len(smart_fields)}")
                st.write(f"Auto mapped: {mapped_count}")

            with col_actions:
                if st.button(
                    "Open", key=f"open_{template.template_id}", use_container_width=True
                ):
                    _set_selected_template_id(template.template_id)
                    st.rerun()

                if st.button(
                    "Delete",
                    key=f"delete_{template.template_id}",
                    use_container_width=True,
                ):
                    result = vm.delete_template(template.template_id)
                    if result.success:
                        if _get_selected_template_id() == template.template_id:
                            _set_selected_template_id(None)
                        st.success(result.message)
                        st.rerun()
                    else:
                        st.error(result.error)


def _render_header(template: DynamicFormTemplate) -> None:
    col_back, col_title = st.columns([1, 6])

    with col_back:
        if st.button("← Back"):
            _set_selected_template_id(None)
            st.rerun()

    with col_title:
        st.subheader(template.name)
        st.caption("Anmeldung smart autofill")


def _render_known_fields(
    vm: FormsVM, template: DynamicFormTemplate, entity_id: str | None
) -> None:
    smart_fields = vm.list_smart_visible_fields(template.template_id)

    if not smart_fields:
        st.info("No known fields prepared yet.")
        return

    preview = vm.build_preview(template.template_id, entity_id)

    if preview is None:
        rows = [
            {
                "Field": item.field.label,
                "Profile field": item.field.profile_field_name,
                "Required": item.field.required,
            }
            for item in smart_fields
        ]
    else:
        rows = [
            {
                "Field": field.label,
                "Profile field": field.profile_field_name,
                "Value": field.value,
                "Required": field.required,
                "Missing": field.is_missing,
            }
            for field in preview.fields
        ]

    st.dataframe(rows, use_container_width=True)


def _render_smart_fill(vm: FormsVM, template: DynamicFormTemplate) -> None:
    st.subheader("Smart Autofill")

    entity_id = _get_active_entity_id()

    if not entity_id:
        st.warning(
            "No active Trusted Profile selected. Please go to Profile and select/create a person first."
        )
        return

    st.markdown("""
        Click one button. NASMI will:

        - detect the PDF fields
        - recognize known Anmeldung fields
        - fill them from the Trusted Profile
        - ignore technical PDF fields
        - export a completed PDF
        """)

    smart_fields = vm.list_smart_visible_fields(template.template_id)
    preview = (
        vm.build_preview(template.template_id, entity_id) if smart_fields else None
    )

    if preview is not None:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Known fields", len(preview.fields))
        with col2:
            st.metric(
                "Required ready",
                f"{preview.readiness.filled_required}/{preview.readiness.total_required}",
            )
        with col3:
            st.metric("Completeness", f"{int(preview.readiness.completeness * 100)}%")

        if preview.readiness.missing_required:
            st.warning("Some required profile data is missing.")
            with st.expander("Missing data", expanded=True):
                for item in preview.readiness.missing_required:
                    st.write(f"- {item}")
        else:
            st.success("Required data is ready.")

    st.divider()

    if st.button("Fill Automatically", type="primary", use_container_width=True):
        prepare = vm.smart_prepare_template(template.template_id)

        if not prepare.success:
            st.error(prepare.error)
            return

        result = vm.generate_filled_pdf(
            template_id=template.template_id,
            entity_id=entity_id,
        )

        if result.success:
            st.session_state[f"filled_pdf_{template.template_id}"] = result.output_path
            st.success(
                f"PDF filled successfully. Filled fields: {result.filled_count}. Missing required: {result.missing_count}."
            )
            st.rerun()
        else:
            st.error(result.error)

    output_path = st.session_state.get(f"filled_pdf_{template.template_id}")

    if output_path and Path(output_path).exists():
        st.success("Your completed PDF is ready.")

        with open(output_path, "rb") as file:
            st.download_button(
                "Download Filled PDF",
                data=file.read(),
                file_name=Path(output_path).name,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    st.divider()

    with st.expander("Show fields NASMI will fill", expanded=False):
        _render_known_fields(vm, template, entity_id)


def _render_advanced(vm: FormsVM, template: DynamicFormTemplate) -> None:
    st.subheader("Advanced")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Analyze PDF Fields", use_container_width=True):
            result = vm.analyze_pdf_form(template.template_id, clear_existing=False)
            if result.success:
                st.success(
                    f"Fields found: {result.field_count}. Created: {result.created_count}. Skipped: {result.skipped_count}."
                )
                st.rerun()
            else:
                st.error(result.error)

    with col2:
        if st.button("Reset And Re-Analyze", use_container_width=True):
            result = vm.analyze_pdf_form(template.template_id, clear_existing=True)
            if result.success:
                prepare = vm.smart_prepare_template(template.template_id)
                if prepare.success:
                    st.success("PDF re-analyzed and prepared.")
                    st.rerun()
                else:
                    st.error(prepare.error)
            else:
                st.error(result.error)

    st.divider()

    smart_fields = vm.list_smart_fields(template.template_id)

    rows = [
        {
            "Label": item.field.label,
            "Mapping": item.field.profile_field_name,
            "Visible": item.is_visible,
            "Group": item.group,
            "Status": item.status,
            "Position": item.position_text,
            "PDF field": item.field.field_name,
        }
        for item in smart_fields
    ]

    st.dataframe(rows, use_container_width=True)

    with st.expander("Raw template data", expanded=False):
        st.json(
            {
                "template": template.__dict__,
                "fields": [
                    field.__dict__ for field in vm.list_fields(template.template_id)
                ],
            }
        )


def _render_workspace(vm: FormsVM, template_id: str) -> None:
    template = vm.get_template(template_id)

    if template is None:
        st.warning("Form not found.")
        _set_selected_template_id(None)
        return

    _render_header(template)

    tab_fill, tab_advanced = st.tabs(["Smart Fill", "Advanced"])

    with tab_fill:
        _render_smart_fill(vm, template)

    with tab_advanced:
        _render_advanced(vm, template)


def render() -> None:
    st.title("Forms")

    vm = FormsVM()
    selected_template_id = _get_selected_template_id()

    if selected_template_id:
        _render_workspace(vm, selected_template_id)
        return

    tab_upload, tab_saved = st.tabs(["Upload PDF", "Saved Forms"])

    with tab_upload:
        _render_create_template(vm)

    with tab_saved:
        _render_templates_list(vm)
