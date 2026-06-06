import streamlit as st

from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get


def render_evidence_panel(case_id: str) -> None:
    st.markdown("### Evidence")

    conflict_id = get(SessionKeys.SELECTED_CONFLICT_ID)
    if not conflict_id:
        st.caption("Select a conflict to view evidence.")
        return

    preview = get(SessionKeys.AUTOFILL_PREVIEW)
    if not preview:
        st.caption("No evidence available.")
        return

    evidence_map: dict = preview.get("evidence", {})
    evidence = evidence_map.get(conflict_id)

    if not evidence:
        st.caption("No evidence available for this conflict.")
        return

    for item in evidence:
        with st.container(border=True):
            st.markdown(f"**Source:** {item.get('source', '—')}")
            st.markdown(f"**Excerpt:** {item.get('excerpt', '—')}")
            st.caption(
                f"Page {item.get('page', '—')} · Confidence: {item.get('confidence', '—')}"
            )
