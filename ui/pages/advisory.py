from __future__ import annotations

import streamlit as st

from processing.llm.advisory_result import AdvisoryResult
from processing.llm.personal_advisor.advice_item import PersonalAdvisoryResult
from ui.services.api_client import list_entities
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
    cached: AdvisoryCache | None = sm.get(SessionKeys.ADVISORY_CACHE)
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
    st.subheader("🧠 Personal Advisory")
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
    st.subheader("📡 Proactive Advisory")
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


def _render_chat(vm: AdvisoryVM, entity_id: str) -> None:
    st.subheader("💬 Ask Your Advisor")

    if "advisory_chat_history" not in st.session_state:
        st.session_state.advisory_chat_history = []

    for msg in st.session_state.advisory_chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input(
        "Ask anything about your profile, documents, or situation..."
    )

    if question:
        st.session_state.advisory_chat_history.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = vm.chat(entity_id, question)
            st.write(answer)

        st.session_state.advisory_chat_history.append(
            {"role": "assistant", "content": answer}
        )


def render() -> None:
    st.title("💡 Advisory")

    entities = list_entities()
    if not entities:
        st.warning("No active entities found in the database.")
        return

    options = {e.display_name: e.entity_id for e in entities}

    current_id: str | None = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
    current_name = next(
        (name for name, eid in options.items() if eid == current_id),
        list(options.keys())[0],
    )

    selected_name = st.selectbox(
        "Select Entity",
        options=list(options.keys()),
        index=list(options.keys()).index(current_name),
    )

    selected_id = options[selected_name]

    if selected_id != current_id:
        sm.set(SessionKeys.ACTIVE_ENTITY_ID, selected_id)
        sm.set(SessionKeys.ADVISORY_CACHE, None)
        st.rerun()

    entity_id = selected_id

    col_refresh, _ = st.columns([1, 9])
    with col_refresh:
        force_refresh = st.button("🔄 Refresh", key="advisory_refresh")

    vm = AdvisoryVM()
    cache = _load_cache(vm, entity_id, force=force_refresh)

    if cache.personal is None and cache.proactive is None:
        st.warning("No advisory data found.")
        return

    if cache.personal:
        display_name = cache.personal.display_name
    elif cache.proactive and cache.proactive.items:
        display_name = cache.proactive.items[0].display_name
    else:
        display_name = selected_name

    st.markdown(f"## {display_name}")
    st.divider()

    if cache.personal:
        _render_personal_advisory(cache.personal)

    if cache.personal and cache.proactive:
        st.divider()

    if cache.proactive:
        _render_proactive_advisory(cache.proactive)

    st.divider()
    _render_chat(vm, entity_id)
