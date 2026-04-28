import streamlit as st
from ui.style import apply_theme

st.set_page_config(
    page_title="NASMI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ── Sidebar ──────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div class='sidebar-logo'>
            <h1>NASMI</h1>
            <p>Neural Automated Secure<br>Management of Information</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # ── System Status Bar ──
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#546e7a;'>DOCUMENTS</div>"
            "<div style='text-align:center;font-size:1.1rem;font-weight:700;color:#4fc3f7;'>—</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#546e7a;'>TRUST SCORE</div>"
            "<div style='text-align:center;font-size:1.1rem;font-weight:700;color:#4fc3f7;'>—</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Review Queue Alert ──
    review_count = 0
    if review_count > 0:
        st.error(f"⚠️ {review_count} items need review", icon=None)
    else:
        st.markdown(
            "<div style='font-size:0.75rem;color:#37474f;text-align:center;'>✔ No pending reviews</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown(
        "<div style='font-size:0.65rem;color:#263238;text-align:center;padding-top:1rem;'>"
        "NASMI v0.1.0 · Local-First · Secure</div>",
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
