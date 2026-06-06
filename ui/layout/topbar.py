import streamlit as st

from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set

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

_CSS = """
<style>
[data-testid="stHorizontalBlock"]:first-of-type {
    background: #0f172a;
    padding: 0.5rem 1.2rem;
    border-radius: 0 0 12px 12px;
    margin-bottom: 1rem;
    align-items: center;
}
[data-testid="stHorizontalBlock"]:first-of-type p strong {
    color: #38bdf8;
    font-size: 1.25rem;
    letter-spacing: 2px;
}
[data-testid="stHorizontalBlock"]:first-of-type button[kind="secondary"] {
    background: transparent !important;
    border: none !important;
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    padding: 0.3rem 0.5rem !important;
    border-radius: 6px !important;
    transition: background 0.2s, color 0.2s;
    white-space: nowrap;
}
[data-testid="stHorizontalBlock"]:first-of-type button[kind="secondary"]:hover {
    background: #1e293b !important;
    color: #f1f5f9 !important;
}
.nav-active {
    background: #1e40af;
    color: #e0f2fe !important;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 0.3rem 0.7rem;
    border-radius: 6px;
    display: inline-block;
    white-space: nowrap;
}
</style>
"""


def _navigate(page: PageId) -> None:
    set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def render_topbar() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    current = get(SessionKeys.CURRENT_PAGE)
    title_col, *nav_cols = st.columns([2] + [1] * len(_NAV_ITEMS))

    with title_col:
        st.markdown("**NASMI**")

    for col, (label, page_id) in zip(nav_cols, _NAV_ITEMS, strict=True):
        with col:
            if current == page_id:
                st.markdown(
                    f'<span class="nav-active">{label}</span>', unsafe_allow_html=True
                )
            else:
                if st.button(label, key=f"nav_{page_id}", use_container_width=True):
                    _navigate(page_id)
