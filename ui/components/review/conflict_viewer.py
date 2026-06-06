import streamlit as st

from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set


def render_conflict_viewer(case_id: str) -> None:
    st.markdown("### Conflicts")

    preview = get(SessionKeys.AUTOFILL_PREVIEW)
    if not preview:
        st.caption("No conflicts detected.")
        return

    conflicts: list = preview.get("conflicts", [])
    if not conflicts:
        st.caption("No conflicts detected.")
        return

    selected_conflict = get(SessionKeys.SELECTED_CONFLICT_ID)

    for conflict in conflicts:
        conflict_id = conflict["id"]
        is_active = selected_conflict == conflict_id

        with st.container(border=True):
            col_label, col_action = st.columns([8, 2])
            with col_label:
                st.markdown(f"**{conflict.get('field', '—')}**")
                st.caption(
                    f"Source A: {conflict.get('value_a', '—')} "
                    f"| Source B: {conflict.get('value_b', '—')}"
                )
            with col_action:
                if not is_active:
                    if st.button("Inspect", key=f"conflict_{conflict_id}"):
                        set(SessionKeys.SELECTED_CONFLICT_ID, conflict_id)
                        st.rerun()
                else:
                    st.markdown("**Inspecting**")
