from __future__ import annotations

import streamlit as st

from infrastructure.db.repositories.sqlite_entity_repository import (
    SqliteEntityRepository,
)
from knowledge.entity import Entity, EntityType
from ui.services.api_client import list_entities
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set

_CSS = """
<style>
.settings-header {
    font-size: 1.6rem;
    font-weight: 800;
    color: #38bdf8;
    letter-spacing: 2px;
    margin-bottom: 0.2rem;
}
.settings-sub {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}
</style>
"""

_ENTITY_TYPES = [
    EntityType.PERSON,
    EntityType.ORGANIZATION,
    EntityType.LOCATION,
    EntityType.CONCEPT,
    EntityType.DOCUMENT,
]

_LANGUAGES = ["de", "en", "ar", "fr", "tr"]


def _save_entity(entity: Entity) -> None:
    from ui.services.api_client import _get_db

    repo = SqliteEntityRepository(_get_db())
    repo.save(entity)


def _create_section() -> None:
    st.markdown("### ➕ Create New Entity")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            display_name = st.text_input("Display Name", placeholder="e.g. John Doe")
        with col2:
            entity_type = st.selectbox("Entity Type", _ENTITY_TYPES)

        col3, col4 = st.columns(2)
        with col3:
            primary_language = st.selectbox("Primary Language", _LANGUAGES)
        with col4:
            st.write("")
            st.write("")
            submit = st.button(
                "Create Entity", type="primary", use_container_width=True
            )

        if submit:
            if not display_name.strip():
                st.error("Display Name is required.")
            else:
                try:
                    entity = Entity.create(
                        entity_type=entity_type,
                        display_name=display_name.strip(),
                        primary_language=primary_language,
                    )
                    _save_entity(entity)
                    set(SessionKeys.ACTIVE_ENTITY_ID, entity.entity_id)
                    st.success(
                        f"✅ Entity '{entity.display_name}' created and activated."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Failed to create entity: {exc}")


def _entities_section() -> None:
    st.markdown("### 👥 Existing Entities")
    entities = list_entities()
    active_id = get(SessionKeys.ACTIVE_ENTITY_ID)

    if not entities:
        st.info("No active entities found. Create one above.")
        return

    for e in entities:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                is_active = e.entity_id == active_id
                label = f"{'🟢 ' if is_active else ''}{e.display_name}"
                st.markdown(f"**{label}**")
                st.caption(f"`{e.entity_type}` · {e.entity_id[:8]}...")
            with col2:
                st.caption(f"Status: {e.status}")
            with col3:
                if not is_active:
                    if st.button(
                        "Activate",
                        key=f"activate_{e.entity_id}",
                        use_container_width=True,
                    ):
                        set(SessionKeys.ACTIVE_ENTITY_ID, e.entity_id)
                        st.rerun()
                else:
                    st.markdown("✅ Active")


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="settings-header">⚙️ Settings</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="settings-sub">Manage entities and system configuration.</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    _create_section()
    st.divider()
    _entities_section()
