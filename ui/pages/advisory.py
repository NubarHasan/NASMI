from __future__ import annotations

import streamlit as st

from processing.llm.advisory_result import AdvisoryResult
from processing.llm.personal_advisor.advice_item import PersonalAdvisoryResult
from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.advisory_cache import AdvisoryCache
from ui.viewmodels.advisory_vm import AdvisoryVM

_SEVERITY_BADGE: dict[str, str] = {
    "critical": "🔴",
    "warning": "⚠️",
    "info": "ℹ️",
}


def _severity_badge(severity: str) -> str:
    return _SEVERITY_BADGE.get(severity, "•")


def _load_cache(vm: AdvisoryVM, entity_id: str, force: bool = False) -> AdvisoryCache:
    cached = sm.get(SessionKeys.ADVISORY_CACHE)
    if not force and cached is not None and cached.entity_id == entity_id:
        return cached
    personal, proactive = vm.refresh(entity_id)
    cache = AdvisoryCache(
        entity_id=entity_id,
        personal=personal,
        proactive=proactive,
    )
    sm.set(SessionKeys.ADVISORY_CACHE, cache)
    return cache


def _render_personal_advisory(result: PersonalAdvisoryResult) -> None:
    st.subheader("Personal Advisory")
    if not result.items:
        st.info("No personal advisory items.")
        return
    if result.llm_summary:
        st.caption(result.llm_summary)
    for item in result.items:
        badge = _severity_badge(item.severity)
        with st.expander(f"{badge}  **{item.title}**"):
            st.write(item.body)
            st.caption(item.suggestion)


def _render_proactive_advisory(result: AdvisoryResult) -> None:
    st.subheader("Proactive Advisory")
    if not result.items:
        st.info("No proactive advisory items.")
        return
    if result.llm_summary:
        st.caption(result.llm_summary)
    for item in result.items:
        badge = _severity_badge(item.severity)
        with st.expander(f"{badge}  **{item.field_name}**  —  {item.message}"):
            st.write(
                f"Expiry: {item.expiry_date}  ·  Days remaining: {item.days_remaining}"
            )
            st.caption(item.suggestion)


def render() -> None:
    vm = AdvisoryVM()
    entity_id = sm.get(SessionKeys.ACTIVE_ENTITY_ID)

    if entity_id is None:
        st.info("No active entity. Select an entity first.")
        return

    force_refresh = st.button("Refresh", key="advisory_refresh")
    cache = _load_cache(vm, entity_id, force=force_refresh)

    if cache.personal is None and cache.proactive is None:
        st.warning("No advisory data found.")
        return

    if cache.personal:
        display_name = cache.personal.display_name
    elif cache.proactive and cache.proactive.items:
        display_name = cache.proactive.items[0].display_name
    else:
        display_name = "Unknown Entity"

    left, right = st.columns([3, 7])

    with left:
        st.markdown(f"## {display_name}")
        st.caption(
            f"Locale: {cache.personal.locale if cache.personal else cache.proactive.locale}"
        )
        st.divider()
        locales = vm.get_supported_locales()
        st.radio(
            "Language", sorted(locales), horizontal=True, label_visibility="collapsed"
        )

    with right:
        if cache.personal:
            _render_personal_advisory(cache.personal)
        if cache.personal and cache.proactive:
            st.divider()
        if cache.proactive:
            _render_proactive_advisory(cache.proactive)
