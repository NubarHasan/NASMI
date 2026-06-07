from __future__ import annotations

import streamlit as st

from ui.services.api_client import (
    create_entity,
    get_entity,
    get_profile_status,
    list_entities,
)
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set
from ui.viewmodels.profile_vm import ProfileFieldRow, ProfileVM

_CSS = """
<style>
.profile-hero {
    padding: 1rem 0 0.5rem;
}
.profile-title {
    color: #38bdf8;
    font-size: 2rem;
    font-weight: 900;
}
.profile-subtitle {
    color: #94a3b8;
    font-size: 0.9rem;
}
.entity-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 1rem;
}
.entity-name {
    color: #f8fafc;
    font-size: 1.35rem;
    font-weight: 900;
}
.entity-meta {
    color: #94a3b8;
    font-size: 0.8rem;
    margin-top: 0.2rem;
}
.status-box {
    background: #082f49;
    border: 1px solid #0369a1;
    border-radius: 16px;
    padding: 1rem;
}
.status-title {
    color: #bae6fd;
    font-size: 1rem;
    font-weight: 900;
}
.status-text {
    color: #e0f2fe;
    font-size: 0.88rem;
    margin-top: 0.4rem;
}
.section-card {
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 0.85rem;
    margin-bottom: 0.5rem;
}
.field-name {
    color: #e2e8f0;
    font-weight: 800;
}
.field-value {
    color: #bae6fd;
}
.field-meta {
    color: #64748b;
    font-size: 0.75rem;
}
.missing-box {
    background: #431407;
    border: 1px solid #ea580c;
    border-radius: 14px;
    padding: 1rem;
}
.ready-box {
    background: #052e16;
    border: 1px solid #16a34a;
    border-radius: 14px;
    padding: 1rem;
}
</style>
"""


def _navigate(page: PageId) -> None:
    set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def _create_entity_form() -> None:
    st.subheader("Create Entity")

    with st.form("create_entity_form", clear_on_submit=False):
        display_name = st.text_input("Display name", placeholder="Example: Nubar Hasan")
        entity_type = st.selectbox(
            "Entity type",
            ["person", "company", "organization", "case", "other"],
            index=0,
        )
        primary_language = st.selectbox(
            "Primary language",
            ["en", "de", "ar", "tr", "fr", "es"],
            index=0,
        )

        submitted = st.form_submit_button("Create and activate", type="primary")

    if submitted:
        try:
            entity = create_entity(
                display_name=display_name,
                entity_type=entity_type,
                primary_language=primary_language,
            )
            set(SessionKeys.ACTIVE_ENTITY_ID, entity.entity_id)
            set(SessionKeys.ACTIVE_USER_ID, entity.entity_id)
            st.success(f"Entity created: {entity.display_name}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _select_existing_entity() -> None:
    entities = list_entities()

    if not entities:
        st.info("No entities exist yet.")
        return

    current_id = get(SessionKeys.ACTIVE_ENTITY_ID)
    options = {f"{e.display_name} · {e.entity_type}": e.entity_id for e in entities}
    labels = list(options.keys())

    current_label = next(
        (label for label, entity_id in options.items() if entity_id == current_id),
        labels[0],
    )

    selected = st.selectbox(
        "Select active entity",
        labels,
        index=labels.index(current_label),
        key="profile_entity_selector",
    )

    selected_id = options[selected]

    if selected_id != current_id:
        set(SessionKeys.ACTIVE_ENTITY_ID, selected_id)
        set(SessionKeys.ACTIVE_USER_ID, selected_id)
        st.rerun()


def _render_active_entity() -> None:
    entity_id = get(SessionKeys.ACTIVE_ENTITY_ID)
    entity = get_entity(entity_id)

    if entity is None:
        st.warning("No active entity selected.")
        return

    status = get_profile_status(entity.entity_id)

    st.markdown(
        f"""
        <div class="entity-card">
            <div class="entity-name">{entity.display_name}</div>
            <div class="entity-meta">ID: {entity.entity_id}</div>
            <div class="entity-meta">Type: {entity.entity_type}</div>
            <div class="entity-meta">Status: {entity.status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Documents", status.documents_count)
    with col2:
        st.metric("Pending Review", status.pending_review_count)
    with col3:
        st.metric("Accepted Facts", status.accepted_facts_count)
    with col4:
        st.metric("Profile", "Ready" if status.profile_exists else "Editable")

    st.write("")

    st.markdown(
        f"""
        <div class="status-box">
            <div class="status-title">Profile Status</div>
            <div class="status-text">{status.next_step}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    if status.documents_count == 0:
        if st.button("Go to Documents", type="primary", use_container_width=True):
            _navigate(PageId.DOCUMENTS)
    elif status.pending_review_count > 0:
        if st.button("Go to Review", type="primary", use_container_width=True):
            _navigate(PageId.REVIEW)


def _render_build_panel(vm: ProfileVM, entity_id: str | None) -> None:
    st.subheader("Build Trusted Profile")

    if not entity_id:
        st.warning("Select or create an entity first.")
        return

    accepted_facts = vm.list_accepted_facts(entity_id)
    snapshot = vm.load_profile(entity_id)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Accepted Facts Available", len(accepted_facts))

    with col2:
        st.metric("Profile Fields", len(snapshot.fields) if snapshot else 0)

    with col3:
        completeness = snapshot.completeness if snapshot else 0.0
        st.metric("Completeness", f"{int(completeness * 100)}%")

    col_build, col_clear = st.columns([1, 1])

    with col_build:
        if st.button(
            "⚡ Build / Refresh from Accepted Facts",
            type="primary",
            use_container_width=True,
        ):
            result = vm.build_from_accepted_facts(entity_id)
            if result.success:
                st.success(
                    f"Profile updated. Added: {result.inserted_count}, updated: {result.updated_count}"
                )
                st.rerun()
            else:
                st.error(result.error)

    with col_clear:
        if st.button("Clear Profile", use_container_width=True):
            result = vm.clear_profile(entity_id)
            if result.success:
                st.success("Profile cleared.")
                st.rerun()
            else:
                st.error(result.error)

    with st.expander("Accepted facts preview", expanded=False):
        if accepted_facts:
            st.dataframe(accepted_facts, use_container_width=True)
        else:
            st.info("No accepted facts found.")


def _render_overview(vm: ProfileVM, fields: tuple[ProfileFieldRow, ...]) -> None:
    st.subheader("Profile Overview")

    completeness = vm.calculate_completeness(fields)
    missing = vm.get_missing_fields(fields)
    sections = vm.get_fields_by_section(fields)
    filled_sections = sum(1 for section_fields in sections.values() if section_fields)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Fields", len(fields))
    with col2:
        st.metric("Completeness", f"{int(completeness * 100)}%")
    with col3:
        st.metric("Missing Required", len(missing))
    with col4:
        st.metric("Sections Used", filled_sections)

    st.progress(completeness)

    if missing:
        st.markdown(
            """
            <div class="missing-box">
                <b style="color:#fed7aa;">Profile is not complete for Anmeldung.</b><br>
                <span style="color:#ffedd5;">Fill the missing required fields below.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="ready-box">
                <b style="color:#bbf7d0;">Profile has the required Anmeldung fields.</b><br>
                <span style="color:#dcfce7;">Ready for the next Forms step.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_missing_fields(vm: ProfileVM, fields: tuple[ProfileFieldRow, ...]) -> None:
    st.subheader("Missing Required Fields")

    missing = vm.get_missing_fields(fields)

    if not missing:
        st.success("No required fields are missing.")
        return

    for field_name in missing:
        st.warning(field_name)

    st.caption("These fields are required for the first Anmeldung-ready profile.")


def _render_sections(vm: ProfileVM, fields: tuple[ProfileFieldRow, ...]) -> None:
    st.subheader("Profile Sections")

    if not fields:
        st.info("No profile fields yet.")
        return

    organized = vm.get_fields_by_section(fields)
    summaries = {item.section: item for item in vm.get_section_summaries(fields)}

    for section, section_fields in organized.items():
        if not section_fields:
            continue

        summary = summaries.get(section)
        suffix = ""
        if summary is not None:
            suffix = f" · {summary.filled_required}/{summary.total_required} required"

        with st.expander(
            f"{section.replace('_', ' ').title()} ({len(section_fields)}){suffix}",
            expanded=True,
        ):
            for field in section_fields:
                st.markdown(
                    f"""
                    <div class="section-card">
                        <div class="field-name">{field.label}</div>
                        <div class="field-value">{field.value}</div>
                        <div class="field-meta">{field.field_name} · {field.source} · confidence: {field.confidence if field.confidence is not None else "n/a"}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_add_field(vm: ProfileVM, entity_id: str | None) -> None:
    st.subheader("Add Profile Field")

    if not entity_id:
        st.warning("Select or create an entity first.")
        return

    with st.form("add_profile_field_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            field_name = st.text_input("Field name", placeholder="given_names")
            label = st.text_input("Label", placeholder="Given Names")

        with col2:
            value = st.text_input("Value")
            source = st.selectbox(
                "Source",
                ["manual", "accepted_fact", "user", "llm", "imported"],
                index=0,
            )

        submitted = st.form_submit_button("Add Field", type="primary")

    if submitted:
        result = vm.add_field(
            entity_id=entity_id,
            field_name=field_name,
            label=label,
            value=value,
            source=source,
        )
        if result.success:
            st.success("Field added.")
            st.rerun()
        else:
            st.error(result.error)


def _render_field_editor(vm: ProfileVM, fields: tuple[ProfileFieldRow, ...]) -> None:
    st.subheader("Editable Profile Fields")

    if not fields:
        st.info("No profile fields yet. Build the profile from accepted facts first.")
        return

    source_options = ["accepted_fact", "manual", "user", "llm", "imported", "unknown"]

    for field in fields:
        title = f"{field.label} · {field.field_name}"

        with st.expander(title, expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.text_input(
                    "Field name",
                    value=field.field_name,
                    key=f"profile_field_name_{field.field_id}",
                    disabled=True,
                )
                label = st.text_input(
                    "Label",
                    value=field.label,
                    key=f"profile_label_{field.field_id}",
                )

            with col2:
                value = st.text_input(
                    "Value",
                    value=field.value,
                    key=f"profile_value_{field.field_id}",
                )

                current_source = field.source
                if current_source not in source_options:
                    current_source = "unknown"

                source = st.selectbox(
                    "Source",
                    source_options,
                    index=source_options.index(current_source),
                    key=f"profile_source_{field.field_id}",
                )

            st.caption(
                f"Confidence: {field.confidence if field.confidence is not None else 'n/a'} · Updated: {field.updated_at}"
            )

            col_save, col_delete = st.columns([1, 1])

            with col_save:
                if st.button(
                    "Save Field",
                    key=f"save_profile_field_{field.field_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    result = vm.update_field(
                        field_id=field.field_id,
                        label=label,
                        value=value,
                        source=source,
                    )
                    if result.success:
                        st.success("Field saved.")
                        st.rerun()
                    else:
                        st.error(result.error)

            with col_delete:
                if st.button(
                    "Delete Field",
                    key=f"delete_profile_field_{field.field_id}",
                    use_container_width=True,
                ):
                    result = vm.delete_field(field.field_id)
                    if result.success:
                        st.success("Field deleted.")
                        st.rerun()
                    else:
                        st.error(result.error)


def _render_profile_json(fields: tuple[ProfileFieldRow, ...]) -> None:
    st.subheader("Profile Data")

    if not fields:
        st.info("Profile is empty.")
        return

    profile_dict = {
        field.field_name: {
            "label": field.label,
            "value": field.value,
            "source": field.source,
            "confidence": field.confidence,
            "updated_at": field.updated_at,
        }
        for field in fields
    }

    st.json(profile_dict)


def _render_trusted_profile() -> None:
    vm = ProfileVM()
    entity_id = get(SessionKeys.ACTIVE_ENTITY_ID)

    if not entity_id:
        st.warning("Create or select an active entity first.")
        return

    snapshot = vm.load_profile(entity_id)
    fields = snapshot.fields if snapshot else ()

    st.subheader("Trusted Profile Center")

    if snapshot is not None:
        st.caption(f"Entity: {snapshot.entity_name} · ID: {snapshot.entity_id}")

    tab_overview, tab_build, tab_missing, tab_sections, tab_edit, tab_add, tab_data = (
        st.tabs(
            [
                "Overview",
                "Build",
                "Missing",
                "Sections",
                "Edit Fields",
                "Add Field",
                "Data",
            ]
        )
    )

    with tab_overview:
        _render_overview(vm, fields)

    with tab_build:
        _render_build_panel(vm, entity_id)

    with tab_missing:
        current_snapshot = vm.load_profile(entity_id)
        current_fields = current_snapshot.fields if current_snapshot else ()
        _render_missing_fields(vm, current_fields)

    with tab_sections:
        current_snapshot = vm.load_profile(entity_id)
        current_fields = current_snapshot.fields if current_snapshot else ()
        _render_sections(vm, current_fields)

    with tab_edit:
        current_snapshot = vm.load_profile(entity_id)
        current_fields = current_snapshot.fields if current_snapshot else ()
        _render_field_editor(vm, current_fields)

    with tab_add:
        _render_add_field(vm, entity_id)

    with tab_data:
        current_snapshot = vm.load_profile(entity_id)
        current_fields = current_snapshot.fields if current_snapshot else ()
        _render_profile_json(current_fields)


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="profile-hero">
            <div class="profile-title">Profile / Entity Start</div>
            <div class="profile-subtitle">Create an entity, build a trusted profile from accepted facts, then edit it before forms.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_start, tab_profile = st.tabs(["Entity Start", "Trusted Profile"])

    with tab_start:
        left, right = st.columns([1, 1.4])

        with left:
            _create_entity_form()
            st.divider()
            _select_existing_entity()

        with right:
            st.subheader("Active Entity")
            _render_active_entity()

    with tab_profile:
        _render_trusted_profile()
