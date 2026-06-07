from __future__ import annotations

import streamlit as st

from ui.services.api_client import get_health
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, set

_CSS = """
<style>
.home-hero {
    padding: 1.5rem 0.5rem 1rem;
}
.home-title {
    font-size: 3rem;
    font-weight: 900;
    color: #38bdf8;
    letter-spacing: 4px;
    margin-bottom: 0;
}
.home-subtitle {
    color: #94a3b8;
    font-size: 1rem;
    margin-top: 0.1rem;
}
.pipeline-badge {
    display: inline-block;
    background: #0f172a;
    border: 1px solid #1e293b;
    color: #7dd3fc;
    font-family: monospace;
    font-size: 0.85rem;
    padding: 0.45rem 1rem;
    border-radius: 999px;
    margin-top: 0.8rem;
}
.metric-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 1rem;
    min-height: 105px;
}
.metric-label {
    color: #94a3b8;
    font-size: 0.8rem;
}
.metric-value {
    color: #f8fafc;
    font-size: 1.7rem;
    font-weight: 900;
    margin-top: 0.15rem;
}
.metric-note {
    color: #64748b;
    font-size: 0.72rem;
    margin-top: 0.3rem;
}
.stage-card {
    background: #082f49;
    border: 1px solid #0369a1;
    border-radius: 16px;
    padding: 1rem;
}
.stage-title {
    color: #bae6fd;
    font-size: 1rem;
    font-weight: 900;
}
.stage-text {
    color: #e0f2fe;
    font-size: 0.88rem;
    margin-top: 0.4rem;
}
.step-ok {
    color: #86efac;
    font-weight: 800;
}
.step-wait {
    color: #fbbf24;
    font-weight: 800;
}
.step-off {
    color: #64748b;
    font-weight: 800;
}
.page-card-title {
    font-weight: 900;
    color: #f8fafc;
    font-size: 1rem;
}
.page-card-desc {
    color: #94a3b8;
    font-size: 0.82rem;
    min-height: 44px;
}
</style>
"""

_PAGES: list[tuple[str, str, str, PageId]] = [
    (
        "👤",
        "Profile",
        "Create/select entity and inspect trusted profile state.",
        PageId.PROFILE,
    ),
    (
        "📄",
        "Documents",
        "Upload source documents and start intake processing.",
        PageId.DOCUMENTS,
    ),
    (
        "🔍",
        "Review",
        "Approve, reject, or edit extracted candidate facts.",
        PageId.REVIEW,
    ),
    ("📋", "Forms", "Use reviewed data to fill structured forms.", PageId.FORMS),
    ("📤", "Outputs", "Generate, view, and export final packages.", PageId.OUTPUTS),
    ("🔎", "Audit", "Trace documents, facts, decisions, and outputs.", PageId.AUDIT),
]


def _navigate(page: PageId) -> None:
    set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def _metric(label: str, value: int | str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _step(label: str, done: bool, active: bool = False) -> str:
    cls = "step-ok" if done else "step-wait" if active else "step-off"
    icon = "✅" if done else "🟡" if active else "⚪"
    return f'<span class="{cls}">{icon} {label}</span>'


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    health = get_health(get(SessionKeys.ACTIVE_ENTITY_ID))

    st.markdown(
        """
        <div class="home-hero">
            <div class="home-title">NASMI</div>
            <div class="home-subtitle">Neural Automated Secure Management of Information</div>
            <div class="pipeline-badge">Entity → Documents → Extraction → Review → Profile → Forms → Output → Audit</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not health.db_ok:
        st.error(f"Database is not available: {health.error}")
        return

    left, right = st.columns([2, 1])

    with left:
        st.markdown("### Pipeline Overview")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            _metric(
                "Entities",
                health.entities_count,
                health.active_entity_name or "No active entity",
            )
        with m2:
            _metric(
                "Documents", health.documents_count, f"{health.sources_count} sources"
            )
        with m3:
            _metric(
                "Extracted Facts",
                health.extracted_facts_count,
                f"{health.accepted_facts_count} accepted",
            )
        with m4:
            _metric("Review Queue", health.pending_review_count, "pending decisions")

        m5, m6, m7, m8 = st.columns(4)
        with m5:
            _metric("Profiles", health.profiles_count, "trusted snapshots")
        with m6:
            _metric("Noise", health.noise_count, "filtered candidates")
        with m7:
            _metric("Outputs", health.outputs_count, "generated files")
        with m8:
            _metric("Audit", health.audit_count, "events")

        st.markdown("### Pipeline Stages")

        entity_done = health.entities_count > 0
        documents_done = health.documents_count > 0
        extraction_done = health.extracted_facts_count > 0
        review_done = health.accepted_facts_count > 0
        profile_done = health.profiles_count > 0
        output_done = health.outputs_count > 0

        stages = [
            _step("Entity", entity_done, not entity_done),
            _step("Documents", documents_done, entity_done and not documents_done),
            _step(
                "Extraction", extraction_done, documents_done and not extraction_done
            ),
            _step("Review", review_done, extraction_done and not review_done),
            _step("Profile", profile_done, review_done and not profile_done),
            _step("Output", output_done, profile_done and not output_done),
        ]

        st.markdown(" → ".join(stages), unsafe_allow_html=True)

    with right:
        st.markdown(
            f"""
            <div class="stage-card">
                <div class="stage-title">Current Stage: {health.pipeline_stage}</div>
                <div class="stage-text">{health.next_step}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        if health.entities_count == 0:
            if st.button(
                "Start with Profile / Entity", type="primary", use_container_width=True
            ):
                _navigate(PageId.PROFILE)
        elif health.documents_count == 0:
            if st.button("Go to Documents", type="primary", use_container_width=True):
                _navigate(PageId.DOCUMENTS)
        elif health.pending_review_count > 0:
            if st.button("Go to Review", type="primary", use_container_width=True):
                _navigate(PageId.REVIEW)
        elif health.profiles_count == 0:
            if st.button("Go to Profile", type="primary", use_container_width=True):
                _navigate(PageId.PROFILE)
        else:
            if st.button("Continue Pipeline", type="primary", use_container_width=True):
                _navigate(PageId.DOCUMENTS)

    st.divider()

    st.markdown("### Pipeline Pages")

    cols = st.columns(3)
    for index, (icon, title, desc, page_id) in enumerate(_PAGES):
        with cols[index % 3], st.container(border=True):
            st.markdown(f"## {icon}")
            st.markdown(
                f'<div class="page-card-title">{title}</div>', unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="page-card-desc">{desc}</div>', unsafe_allow_html=True
            )
            if st.button(
                "Open →", key=f"home_open_{page_id}", use_container_width=True
            ):
                _navigate(page_id)
