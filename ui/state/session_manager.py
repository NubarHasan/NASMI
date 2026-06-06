from typing import Any

import streamlit as st

from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys


def _make_default(key: SessionKeys) -> Any:
    mutable_lists = {
        SessionKeys.REVIEW_QUEUE,
        SessionKeys.DOCUMENT_LIST,
        SessionKeys.OUTPUT_LIST,
    }
    mutable_dicts = {
        SessionKeys.AUDIT_FILTERS,
    }
    scalar_defaults: dict[SessionKeys, Any] = {
        SessionKeys.ACTIVE_USER_ID: None,
        SessionKeys.ACTIVE_ENTITY_ID: None,
        SessionKeys.CURRENT_PAGE: PageId.HOME,
        SessionKeys.SELECTED_DOCUMENT_ID: None,
        SessionKeys.SELECTED_REVIEW_CASE_ID: None,
        SessionKeys.SELECTED_CONFLICT_ID: None,
        SessionKeys.SELECTED_FORM_TEMPLATE_ID: None,
        SessionKeys.SELECTED_SUBMISSION_ID: None,
        SessionKeys.SELECTED_OUTPUT_ID: None,
        SessionKeys.PROFILE_SNAPSHOT: None,
        SessionKeys.AUTOFILL_PREVIEW: None,
        SessionKeys.PROCESSING_JOB_ID: None,
        SessionKeys.PROCESSING_STATUS: None,
        SessionKeys.ADVISORY_CACHE: None,
        SessionKeys.AUDIT_CHAIN: None,
        SessionKeys.AUDIT_RESULT: None,
        SessionKeys.AUDIT_SELECTED: None,
        SessionKeys.PENDING_SUBMISSION_ID: None,
    }
    if key in mutable_lists:
        return []
    if key in mutable_dicts:
        return {}
    return scalar_defaults[key]


def init_session() -> None:
    for key in SessionKeys:
        if key not in st.session_state:
            st.session_state[key] = _make_default(key)


def get(key: SessionKeys) -> Any:
    return st.session_state.get(key, _make_default(key))


def set(key: SessionKeys, value: Any) -> None:
    st.session_state[key] = value


def reset(key: SessionKeys) -> None:
    st.session_state[key] = _make_default(key)


def reset_selection() -> None:
    for key in (
        SessionKeys.SELECTED_DOCUMENT_ID,
        SessionKeys.SELECTED_REVIEW_CASE_ID,
        SessionKeys.SELECTED_CONFLICT_ID,
        SessionKeys.SELECTED_FORM_TEMPLATE_ID,
        SessionKeys.SELECTED_SUBMISSION_ID,
        SessionKeys.SELECTED_OUTPUT_ID,
        SessionKeys.AUDIT_SELECTED,
        SessionKeys.PENDING_SUBMISSION_ID,
        SessionKeys.AUTOFILL_PREVIEW,
        SessionKeys.ADVISORY_CACHE,
    ):
        st.session_state[key] = _make_default(key)
