from __future__ import annotations

import streamlit as st

from ui.layout.navigation import nav_items
from ui.services.api_client import list_entities, resolve_active_entity_id
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set

_CSS = """
<style>
.nasmi-topbar {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 1rem;
}
.nasmi-brand {
    color: #38bdf8;
    font-size: 1.35rem;
    font-weight: 900;
    letter-spacing: 3px;
    line-height: 1;
}
.nasmi-subtitle {
    color: #64748b;
    font-size: 0.72rem;
    margin-top: 0.15rem;
}
.nav-active {
    background: #1d4ed8;
    color: #e0f2fe;
    font-size: 0.78rem;
    font-weight: 800;
    padding: 0.38rem 0.5rem;
    border-radius: 8px;
    display: block;
    text-align: center;
    white-space: nowrap;
}
.entity-empty {
    color: #f59e0b;
    background: #451a03;
    border: 1px solid #92400e;
    border-radius: 10px;
    padding: 0.45rem 0.7rem;
    font-size: 0.8rem;
    text-align: center;
}
</style>
"""


def _navigate(page: PageId) -> None:
    set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def _sync_active_entity() -> None:
    current_id = get(SessionKeys.ACTIVE_ENTITY_ID)
    resolved_id = resolve_active_entity_id(current_id)
    if resolved_id != current_id:
        set(SessionKeys.ACTIVE_ENTITY_ID, resolved_id)
        set(SessionKeys.ACTIVE_USER_ID, resolved_id)


def render_topbar() -> None:
    _sync_active_entity()
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown('<div class="nasmi-topbar">', unsafe_allow_html=True)

    items = nav_items()
    current = PageId(get(SessionKeys.CURRENT_PAGE))
    title_col, entity_col, *nav_cols = st.columns([1.4, 1.8] + [1] * len(items))

    with title_col:
        st.markdown('<div class="nasmi-brand">NASMI</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="nasmi-subtitle">Secure Information Pipeline</div>',
            unsafe_allow_html=True,
        )

    with entity_col:
        entities = list_entities()
        current_id = get(SessionKeys.ACTIVE_ENTITY_ID)

        if entities:
            options = {
                f"{e.display_name} · {e.entity_type}": e.entity_id for e in entities
            }
            labels = list(options.keys())
            current_label = next(
                (
                    label
                    for label, entity_id in options.items()
                    if entity_id == current_id
                ),
                labels[0],
            )
            selected = st.selectbox(
                "Active entity",
                labels,
                index=labels.index(current_label),
                label_visibility="collapsed",
                key="topbar_active_entity",
            )
            selected_id = options[selected]
            if selected_id != current_id:
                set(SessionKeys.ACTIVE_ENTITY_ID, selected_id)
                set(SessionKeys.ACTIVE_USER_ID, selected_id)
                st.rerun()
        else:
            st.markdown(
                '<div class="entity-empty">No active entity · Start from Profile</div>',
                unsafe_allow_html=True,
            )

    for col, (label, page_id) in zip(nav_cols, items, strict=True):
        with col:
            if current == page_id:
                st.markdown(
                    f'<span class="nav-active">{label}</span>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"nav_{page_id}", use_container_width=True):
                    _navigate(page_id)

    st.markdown("</div>", unsafe_allow_html=True)
