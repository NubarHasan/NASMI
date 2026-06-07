from __future__ import annotations

import streamlit as st

from ui.services.api_client import get_health
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import set

_CARDS: list[tuple[str, str, str, PageId]] = [
    (
        "📄",
        "Documents",
        "Upload and manage source documents for processing and review.",
        PageId.DOCUMENTS,
    ),
    (
        "🔍",
        "Review",
        "Inspect extracted data, resolve conflicts, and approve results.",
        PageId.REVIEW,
    ),
    (
        "📋",
        "Forms",
        "Fill and submit structured forms generated from reviewed data.",
        PageId.FORMS,
    ),
    (
        "💡",
        "Advisory",
        "Query the LLM advisor for guidance based on processed knowledge.",
        PageId.ADVISORY,
    ),
    ("📤", "Outputs", "View and export generated outputs and reports.", PageId.OUTPUTS),
    (
        "🔎",
        "Audit",
        "Trace and verify the full audit chain of all operations.",
        PageId.AUDIT,
    ),
]

_CSS = """
<style>
.home-hero {
    text-align: center;
    padding: 2.5rem 1rem 1rem;
}
.home-hero h1 {
    font-size: 3rem;
    font-weight: 800;
    color: #38bdf8;
    letter-spacing: 4px;
    margin-bottom: 0.2rem;
}
.home-hero p {
    color: #94a3b8;
    font-size: 1rem;
    margin-bottom: 0.5rem;
}
.pipeline-badge {
    display: inline-block;
    background: #1e293b;
    color: #7dd3fc;
    font-family: monospace;
    font-size: 0.9rem;
    padding: 0.4rem 1.2rem;
    border-radius: 20px;
    margin-bottom: 1.5rem;
    letter-spacing: 1px;
}
.card-icon  { font-size: 2rem; margin-bottom: 0.4rem; }
.card-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin-bottom: 0.3rem; }
.card-desc  { font-size: 0.82rem; color: #94a3b8; min-height: 48px; }
.status-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0;
    border-bottom: 1px solid #1e293b;
    font-size: 0.88rem;
}
.status-label { color: #94a3b8; flex: 1; }
.status-badge-ok  {
    background: #14532d;
    color: #86efac;
    padding: 0.15rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}
.status-badge-err {
    background: #1e293b;
    color: #f87171;
    padding: 0.15rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}
</style>
"""


def _navigate(page: PageId) -> None:
    set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def _status_row(icon: str, label: str, value: str, ok: bool) -> str:
    badge_class = "status-badge-ok" if ok else "status-badge-err"
    return f"""
    <div class="status-row">
        <span>{icon}</span>
        <span class="status-label">{label}</span>
        <span class="{badge_class}">{value}</span>
    </div>"""


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        """
    <div class="home-hero">
        <h1>NASMI</h1>
        <p>Neural Automated Secure Management of Information</p>
        <span class="pipeline-badge">Document → Knowledge → Review → Forms → Output</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    cols = st.columns(len(_CARDS))
    for col, (icon, title, desc, page_id) in zip(cols, _CARDS, strict=True):
        with col, st.container(border=True):
            st.markdown(f'<div class="card-icon">{icon}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="card-title">{title}</div>', unsafe_allow_html=True
            )
            st.markdown(f'<div class="card-desc">{desc}</div>', unsafe_allow_html=True)
            if st.button(
                "Open →",
                key=f"home_open_{page_id}",
                type="primary",
                use_container_width=True,
            ):
                _navigate(page_id)

    st.divider()

    health = get_health()

    left, _ = st.columns([1, 2])
    with left:
        st.markdown("### 🖥️ System Status")

        rows = "".join(
            [
                _status_row(
                    "🔌",
                    "Backend",
                    "Connected" if health.db_ok else "Not Connected",
                    health.db_ok,
                ),
                _status_row(
                    "📥",
                    "Review Queue",
                    (
                        f"{health.review_queue_count} pending"
                        if health.db_ok
                        else "Unknown"
                    ),
                    health.db_ok,
                ),
                _status_row(
                    "🗄️",
                    "Knowledge Vault",
                    (
                        f"{health.knowledge_facts_count} facts"
                        if health.db_ok
                        else "Unknown"
                    ),
                    health.db_ok,
                ),
            ]
        )
        st.markdown(rows, unsafe_allow_html=True)

        if health.error:
            st.caption(f"⚠️ {health.error}")
