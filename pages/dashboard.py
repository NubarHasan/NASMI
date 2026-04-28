import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header("🏠", "Dashboard", "System overview — live status of your knowledge base")

# ── Mock State (replace with DB calls later) ──
trust_score = None
total_docs = None
active_entities = None
review_pending = None
contradictions = None
quality_score = None

# ── KPI Row ───────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("🔒 Trust Score", f"{trust_score}%" if trust_score else "—")
c2.metric("📄 Documents", total_docs or "—")
c3.metric("🧠 Entities", active_entities or "—")
c4.metric("✋ Review Queue", review_pending or "—")
c5.metric("⚠️ Contradictions", contradictions or "—")
c6.metric("📊 Quality Score", f"{quality_score}%" if quality_score else "—")

st.divider()

# ── Main Layout ───────────────────────────────────────
col_main, col_side = st.columns([3, 1])

with col_main:

    # ── Document Lifecycle Status ──
    st.markdown("#### 📄 Document Lifecycle")
    lc_cols = st.columns(5)
    for col, (label, status) in zip(
        lc_cols,
        [
            ("Uploaded", "new"),
            ("Processing", "pending"),
            ("Reviewed", "new"),
            ("Active", "active"),
            ("Expired", "expired"),
        ],
    ):
        col.markdown(
            f"<div class='nasmi-card' style='text-align:center;'>"
            f"<div style='font-size:1.4rem;font-weight:700;color:#4fc3f7;'>—</div>"
            f"<div style='margin-top:0.3rem;'>{badge(label, status)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Recent Activity ──
    st.markdown("#### 🕐 Recent Activity")
    st.markdown(
        "<div class='nasmi-card' style='color:#37474f;text-align:center;padding:2rem;'>"
        "No activity yet — upload your first document to get started."
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Quality Breakdown ──
    st.markdown("#### 📊 Knowledge Quality Breakdown")
    q_cols = st.columns(3)
    for col, label in zip(q_cols, ["Completeness", "Freshness", "Consistency"]):
        col.markdown(
            f"<div class='nasmi-card' style='text-align:center;'>"
            f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
            f"letter-spacing:1px;'>{label}</div>"
            f"<div style='font-size:1.6rem;font-weight:700;color:#4fc3f7;margin-top:0.4rem;'>—</div>"
            f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>No data yet</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

with col_side:

    # ── System Health ──
    st.markdown("#### 🟢 System Health")
    for service, ok in [
        ("Database", True),
        ("OCR Engine", False),
        ("Ollama LLM", False),
        ("NER Engine", False),
    ]:
        dot = "🟢" if ok else "🔴"
        color = "#a5d6a7" if ok else "#ef9a9a"
        st.markdown(
            f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:0.6rem 1rem;'>"
            f"<span style='font-size:0.85rem;color:#90a4ae;'>{service}</span>"
            f"<span>{dot}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Quick Actions ──
    st.markdown("#### ⚡ Quick Actions")
    st.button("📄 Upload Document", use_container_width=True)
    st.button("🔍 Search Knowledge", use_container_width=True)
    st.button("✋ Review Queue", use_container_width=True)
    st.button("📤 Export Profile", use_container_width=True)

    st.divider()

    # ── Alerts ──
    st.markdown("#### 🔔 Alerts")
    st.markdown(
        "<div class='nasmi-card' style='color:#37474f;text-align:center;"
        "font-size:0.8rem;padding:1rem;'>"
        "No alerts at this time."
        "</div>",
        unsafe_allow_html=True,
    )
