import streamlit as st

from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set


def render_review_queue() -> None:
    st.markdown("### Review Queue")

    queue: list = get(SessionKeys.REVIEW_QUEUE)
    selected = get(SessionKeys.SELECTED_REVIEW_CASE_ID)

    if not queue:
        st.caption("No cases in queue.")
        return

    for case in queue:
        case_id = case["id"]
        label = case.get("label", case_id)
        is_active = selected == case_id

        if is_active:
            st.markdown(f"**→ {label}**")
        else:
            if st.button(label, key=f"queue_{case_id}"):
                set(SessionKeys.SELECTED_REVIEW_CASE_ID, case_id)
                st.rerun()
