from __future__ import annotations

from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, reset_selection, set

_NAV_ITEMS: list[tuple[str, PageId]] = [
    ("🏠 Home", PageId.HOME),
    ("📄 Documents", PageId.DOCUMENTS),
    ("🔍 Review", PageId.REVIEW),
    ("👤 Profile", PageId.PROFILE),
    ("📋 Forms", PageId.FORMS),
    ("💡 Advisory", PageId.ADVISORY),
    ("📤 Outputs", PageId.OUTPUTS),
    ("🔎 Audit", PageId.AUDIT),
    ("⚙️ Settings", PageId.SETTINGS),
]


def navigate_to(page: PageId) -> None:
    import streamlit as st

    reset_selection()
    set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def get_current_page() -> PageId:
    return PageId(get(SessionKeys.CURRENT_PAGE))


def is_active(page: PageId) -> bool:
    return get_current_page() == page


def nav_items() -> list[tuple[str, PageId]]:
    return _NAV_ITEMS
