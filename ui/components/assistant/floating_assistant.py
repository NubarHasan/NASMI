from __future__ import annotations

import streamlit as st

from ui.services.api_client import list_entities
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set
from ui.viewmodels.advisory_vm import AdvisoryVM


def _get_active_entity_id() -> str | None:
    active_entity_id = get(SessionKeys.ACTIVE_ENTITY_ID)
    if active_entity_id:
        return str(active_entity_id)

    entities = list_entities()
    if not entities:
        return None

    entity_id = entities[0].entity_id
    set(SessionKeys.ACTIVE_ENTITY_ID, entity_id)
    return entity_id


def _open_advisory_bubble() -> None:
    st.session_state["nasmi_advisory_bubble_open"] = True


def _close_advisory_bubble() -> None:
    st.session_state["nasmi_advisory_bubble_open"] = False


def _render_bubble_css() -> None:
    st.markdown(
        """
        <style>
        .nasmi-advisory-bubble {
            position: fixed;
            right: 1.5rem;
            bottom: 1.5rem;
            width: 4rem;
            height: 4rem;
            border-radius: 999px;
            background: linear-gradient(135deg, #1f6feb, #7c3aed);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.7rem;
            box-shadow: 0 16px 40px rgba(0,0,0,0.28);
            z-index: 999999;
            pointer-events: none;
        }

        div[data-testid="stButton"] button[kind="secondary"] {
            border-radius: 999px;
        }

        .nasmi-advisory-panel {
            position: fixed;
            right: 1.5rem;
            bottom: 6.2rem;
            width: 28rem;
            max-width: calc(100vw - 3rem);
            max-height: 75vh;
            overflow-y: auto;
            background: #ffffff;
            border: 1px solid rgba(49, 51, 63, 0.15);
            border-radius: 1rem;
            box-shadow: 0 18px 55px rgba(0,0,0,0.28);
            padding: 1rem;
            z-index: 999998;
        }

        @media (prefers-color-scheme: dark) {
            .nasmi-advisory-panel {
                background: #0e1117;
                border: 1px solid rgba(250, 250, 250, 0.15);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_open_button() -> None:
    st.markdown('<div class="nasmi-advisory-bubble">🧠</div>', unsafe_allow_html=True)

    col_left, col_button = st.columns([10, 1])
    with col_button:
        if st.button(
            "🧠",
            key="nasmi_open_advisory_bubble",
            help="Open NASMI Advisory Assistant",
            use_container_width=True,
        ):
            _open_advisory_bubble()
            st.rerun()


def _render_advisory_chat(entity_id: str) -> None:
    vm = AdvisoryVM()

    if "nasmi_advisory_bubble_history" not in st.session_state:
        st.session_state["nasmi_advisory_bubble_history"] = [
            {
                "role": "assistant",
                "content": (
                    "I am your NASMI Advisory Assistant. "
                    "Ask me about your profile, documents, extracted facts, risks, deadlines, or next steps."
                ),
            }
        ]

    st.markdown("### 🧠 NASMI Advisory")
    st.caption(f"Active entity: `{entity_id}`")

    if st.button("Close", key="nasmi_close_advisory_bubble"):
        _close_advisory_bubble()
        st.rerun()

    st.divider()

    for message in st.session_state["nasmi_advisory_bubble_history"][-8:]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask advisory assistant")

    if question:
        st.session_state["nasmi_advisory_bubble_history"].append(
            {"role": "user", "content": question}
        )

        with st.spinner("NASMI Advisory is thinking..."):
            answer = vm.chat(entity_id, question)

        st.session_state["nasmi_advisory_bubble_history"].append(
            {"role": "assistant", "content": answer}
        )

        st.rerun()


def render_floating_assistant() -> None:
    _render_bubble_css()

    if "nasmi_advisory_bubble_open" not in st.session_state:
        st.session_state["nasmi_advisory_bubble_open"] = False

    _render_open_button()

    if not st.session_state["nasmi_advisory_bubble_open"]:
        return

    entity_id = _get_active_entity_id()

    with st.container():
        st.markdown('<div class="nasmi-advisory-panel">', unsafe_allow_html=True)

        if entity_id is None:
            st.warning("No active entity found. Create or select an entity first.")
            if st.button("Close", key="nasmi_close_no_entity_bubble"):
                _close_advisory_bubble()
                st.rerun()
        else:
            _render_advisory_chat(entity_id)

        st.markdown("</div>", unsafe_allow_html=True)
