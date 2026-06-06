import streamlit as st

from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get


def render_case_header(case_id: str) -> None:
    st.markdown("### Review Case")
    st.markdown(f"**Case ID:** `{case_id}`")

    snapshot = get(SessionKeys.PROFILE_SNAPSHOT)
    if snapshot:
        doc_ref = snapshot.get("document_reference", "—")
        entity = snapshot.get("entity_name", "—")
        st.markdown(f"**Document:** {doc_ref}")
        st.markdown(f"**Entity:** {entity}")
