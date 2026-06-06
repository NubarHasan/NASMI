from __future__ import annotations

import streamlit as st

from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.profile_models import FactStatus, ProfileFact, ProfileSnapshot
from ui.viewmodels.profile_vm import ProfileVM

_STATUS_BADGE: dict[FactStatus, str] = {
    FactStatus.CONFIRMED: "✅",
    FactStatus.UNVERIFIED: "⚠️",
    FactStatus.CONFLICTED: "🔴",
}


def _render_entity_summary(snapshot: ProfileSnapshot, conflict_count: int) -> None:
    st.markdown(f"## {snapshot.entity_name}")
    st.caption(f"ID: {snapshot.entity_id}")
    st.divider()

    col_conf, col_facts, col_conflicts = st.columns(3)
    with col_conf:
        st.metric(
            "Confidence", f"{snapshot.confidence:.0%}" if snapshot.confidence else "—"
        )
    with col_facts:
        st.metric("Facts", len(snapshot.facts))
    with col_conflicts:
        st.metric("Conflicts", conflict_count)

    st.divider()
    if st.button("Refresh", key="profile_refresh"):
        sm.reset(SessionKeys.PROFILE_SNAPSHOT)
        st.rerun()


def _render_fact_row(fact: ProfileFact) -> None:
    badge = _STATUS_BADGE[fact.status]
    with st.expander(f"{badge}  **{fact.field}**  —  {fact.value}"):
        if not fact.sources:
            st.caption("No sources.")
            return
        for src in fact.sources:
            col_type, col_excerpt, col_conf = st.columns([2, 6, 1])
            with col_type:
                st.caption(src.document_type)
            with col_excerpt:
                st.write(src.excerpt)
            with col_conf:
                st.caption(f"{src.confidence:.0%}" if src.confidence else "—")


def _render_facts_table(
    snapshot: ProfileSnapshot, filter_status: FactStatus | None
) -> None:
    facts = (
        snapshot.facts
        if filter_status is None
        else tuple(f for f in snapshot.facts if f.status is filter_status)
    )
    if not facts:
        st.info("No facts match the selected filter.")
        return
    for fact in facts:
        _render_fact_row(fact)


def _render_filter_bar() -> FactStatus | None:
    options: dict[str, FactStatus | None] = {
        "All": None,
        "✅ Confirmed": FactStatus.CONFIRMED,
        "⚠️ Unverified": FactStatus.UNVERIFIED,
        "🔴 Conflicted": FactStatus.CONFLICTED,
    }
    choice = st.radio(
        "Filter",
        list(options.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    return options[choice]


def render() -> None:
    vm = ProfileVM()
    entity_id = sm.get(SessionKeys.ACTIVE_ENTITY_ID)

    if entity_id is None:
        st.info("No active entity. Select an entity first.")
        return

    snapshot = vm.load_profile(entity_id)

    if snapshot is None:
        st.error(f"Profile not found for entity '{entity_id}'.")
        return

    conflict_count = vm.count_conflicts(snapshot)
    left, right = st.columns([3, 7])

    with left:
        _render_entity_summary(snapshot, conflict_count)

    with right:
        st.subheader("Knowledge Profile")
        filter_status = _render_filter_bar()
        st.divider()
        _render_facts_table(snapshot, filter_status)
