import streamlit as st
from ui.style import apply_theme
from db.database import Database
from core.event_bus import bus
from core.events import Event, EventType
from config import APP

st.set_page_config(
    page_title=APP["name"],
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()


# ── Session State Init (runs once per session) ────────
def _load_state() -> None:
    with Database() as db:
        doc_row = db.fetchone("SELECT COUNT(*) as cnt FROM documents")
        review_row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM review_queue WHERE status = 'pending'"
        )
        conflict_row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM contradictions WHERE status = 'open'"
        )
        trust_row = db.fetchone("SELECT AVG(confidence) as avg FROM knowledge")
        jobs_row = db.fetchone(
            "SELECT COUNT(*) as cnt FROM processing_jobs WHERE status = 'running'"
        )

    st.session_state["doc_count"] = int(doc_row["cnt"]) if doc_row else 0
    st.session_state["review_count"] = int(review_row["cnt"]) if review_row else 0
    st.session_state["conflict_count"] = int(conflict_row["cnt"]) if conflict_row else 0
    st.session_state["jobs_running"] = int(jobs_row["cnt"]) if jobs_row else 0
    trust_val = trust_row["avg"] if trust_row else None
    st.session_state["trust_label"] = (
        f"{int(float(trust_val or 0) * 100)}%" if trust_val else "—"
    )


def _on_state_change(event: Event) -> None:
    _load_state()


if "db_initialized" not in st.session_state:
    db = Database()
    db.initialize()
    st.session_state["db_initialized"] = True
    _load_state()

    for ev in [
        EventType.DOCUMENT_UPLOADED,
        EventType.ENTITY_VALIDATED,
        EventType.CONFLICT_DETECTED,
        EventType.REVIEW_REQUIRED,
        EventType.ENTITY_MERGED,
    ]:
        bus.subscribe(ev, _on_state_change)


# ── Sidebar ───────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div class='sidebar-logo'>"
        "<h1>NASMI</h1>"
        "<p>Neural Automated Secure<br>Management of Information</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#546e7a;'>DOCUMENTS</div>"
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;color:#4fc3f7;'>{st.session_state['doc_count']}</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#546e7a;'>TRUST SCORE</div>"
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;color:#4fc3f7;'>{st.session_state['trust_label']}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#546e7a;'>CONFLICTS</div>"
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;color:#ef9a9a;'>{st.session_state['conflict_count']}</div>",
            unsafe_allow_html=True,
        )
    with col_d:
        jobs = st.session_state["jobs_running"]
        jobs_color = "#a5d6a7" if jobs == 0 else "#fff176"
        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#546e7a;'>RUNNING</div>"
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;color:{jobs_color};'>{jobs}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    if st.session_state["review_count"] > 0:
        st.error(f"⚠️ {st.session_state['review_count']} items need review")
    else:
        st.markdown(
            "<div style='font-size:0.75rem;color:#37474f;text-align:center;'>✔ No pending reviews</div>",
            unsafe_allow_html=True,
        )

    if st.button("🔄 Refresh", use_container_width=True):
        _load_state()
        st.rerun()

    st.divider()
    st.markdown(
        f"<div style='font-size:0.65rem;color:#263238;text-align:center;padding-top:1rem;'>"
        f"NASMI v{APP['version']} · Local-First · Secure</div>",
        unsafe_allow_html=True,
    )


# ── Pages ─────────────────────────────────────────────
pages = {
    "🏠 Dashboard": "pages/dashboard.py",
    "📄 Upload": "pages/upload.py",
    "📝 Smart Form Filler": "pages/form_filler.py",
    "🔍 Search & Query": "pages/search.py",
    "🧠 Knowledge Base": "pages/knowledge_base.py",
    "📒 Address & Field Book": "pages/address_field_book.py",
    "📅 Timeline": "pages/timeline.py",
    "⚠️ Contradictions": "pages/contradictions.py",
    "✋ Review Queue": "pages/review_queue.py",
    "🔔 Update Center": "pages/update_center.py",
    "🪪 Identity": "pages/identity.py",
    "📤 Export": "pages/export.py",
    "📋 Logs": "pages/logs.py",
    "⚙️ Settings": "pages/settings.py",
}

pg = st.navigation([st.Page(path, title=name) for name, path in pages.items()])
pg.run()
