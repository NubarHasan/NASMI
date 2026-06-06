import streamlit as st

from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set


def render_decision_bar(case_id: str) -> None:
    st.markdown("### Decision")

    col_accept, col_reject, col_edit, col_spacer = st.columns([2, 2, 2, 6])

    with col_accept:
        if st.button("✓ Accept", key=f"decision_accept_{case_id}", type="primary"):
            set(SessionKeys.PROCESSING_STATUS, "accepted")
            st.rerun()

    with col_reject:
        if st.button("✗ Reject", key=f"decision_reject_{case_id}"):
            set(SessionKeys.PROCESSING_STATUS, "rejected")
            st.rerun()

    with col_edit:
        if st.button("✎ Edit", key=f"decision_edit_{case_id}"):
            set(SessionKeys.PROCESSING_STATUS, "editing")
            st.rerun()

    status = get(SessionKeys.PROCESSING_STATUS)
    if status:
        st.caption(f"Status: {status}")
