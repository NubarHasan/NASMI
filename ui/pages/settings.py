from __future__ import annotations

import streamlit as st

from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys


def render() -> None:
    st.title("Settings")

    st.subheader("Session")
    if st.button("Reset All Session Data", type="primary"):
        for key in SessionKeys:
            sm.reset(key)
        st.success("Session reset.")
        st.rerun()

    st.divider()

    st.subheader("Active User")
    user_id: str | None = sm.get(SessionKeys.ACTIVE_USER_ID)
    entity_id: str | None = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
    st.write(f"**User ID:** {user_id or '—'}")
    st.write(f"**Entity ID:** {entity_id or '—'}")
