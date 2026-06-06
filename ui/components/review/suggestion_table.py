import streamlit as st

from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get


def render_suggestion_table(case_id: str) -> None:
    st.markdown("### Suggestions")

    preview = get(SessionKeys.AUTOFILL_PREVIEW)
    if not preview:
        st.caption("No suggestions available.")
        return

    suggestions: list = preview.get("suggestions", [])
    if not suggestions:
        st.caption("No suggestions available.")
        return

    for item in suggestions:
        col_field, col_value, col_status = st.columns([3, 5, 2])
        with col_field:
            st.markdown(f"`{item.get('field', '—')}`")
        with col_value:
            st.markdown(item.get("value", "—"))
        with col_status:
            status = item.get("status", "pending")
            if status == "accepted":
                st.success("Accepted")
            elif status == "rejected":
                st.error("Rejected")
            else:
                st.warning("Pending")
