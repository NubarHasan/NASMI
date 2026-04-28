from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database
from knowledge.quality_engine import QualityEngine
import httpx

apply_theme()
page_header("🏠", "Dashboard", "System overview — live status of your knowledge base")


# ── Helpers ───────────────────────────────────────────
def _check_ollama() -> bool:
    try:
        r = httpx.get("http://localhost:11434", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _load_stats() -> dict:
    try:
        with Database() as db:
            total_docs = db.fetchone("SELECT COUNT(*) as c FROM documents")
            active_entities = db.fetchone(
                "SELECT COUNT(*) as c FROM knowledge_objects WHERE state = ?",
                ("ACTIVE",),
            )
            review_pending = db.fetchone(
                "SELECT COUNT(*) as c FROM review_queue WHERE resolved = 0"
            )
            contradictions = db.fetchone(
                "SELECT COUNT(*) as c FROM conflicts WHERE resolved = 0"
            )
            lifecycle_counts = db.fetchall(
                "SELECT status, COUNT(*) as c FROM documents GROUP BY status"
            )
            recent_events = db.fetchall(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT 8"
            )
        return {
            "total_docs": (total_docs or {}).get("c", 0),
            "active_entities": (active_entities or {}).get("c", 0),
            "review_pending": (review_pending or {}).get("c", 0),
            "contradictions": (contradictions or {}).get("c", 0),
            "lifecycle": {r["status"]: r["c"] for r in lifecycle_counts},
            "recent_events": recent_events,
        }
    except Exception:
        return {
            "total_docs": 0,
            "active_entities": 0,
            "review_pending": 0,
            "contradictions": 0,
            "lifecycle": {},
            "recent_events": [],
        }


def _load_quality() -> dict:
    try:
        qe = QualityEngine()
        return qe.system_summary()
    except Exception:
        return {
            "trust_score": None,
            "completeness": None,
            "freshness": None,
            "consistency": None,
        }


# ── Load Data ─────────────────────────────────────────
stats = _load_stats()
quality = _load_quality()

trust_score = quality.get("trust_score")
quality_score = quality.get("trust_score")
total_docs = stats["total_docs"] or None
active_entities = stats["active_entities"] or None
review_pending = stats["review_pending"] or None
contradictions = stats["contradictions"] or None

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
    lc_map = stats["lifecycle"]
    lc_cols = st.columns(5)
    for col, (label, status, key) in zip(
        lc_cols,
        [
            ("Uploaded", "new", "UPLOADED"),
            ("Processing", "pending", "PROCESSING"),
            ("Reviewed", "new", "REVIEWED"),
            ("Active", "active", "ACTIVE"),
            ("Expired", "expired", "EXPIRED"),
        ],
    ):
        count = lc_map.get(key, 0)
        col.markdown(
            f"<div class='nasmi-card' style='text-align:center;'>"
            f"<div style='font-size:1.4rem;font-weight:700;color:#4fc3f7;'>{count if count else '—'}</div>"
            f"<div style='margin-top:0.3rem;'>{badge(label, status)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Recent Activity ──
    st.markdown("#### 🕐 Recent Activity")
    recent = stats["recent_events"]
    if recent:
        for ev in recent:
            st.markdown(
                f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:0.5rem 1rem;'>"
                f"<span style='font-size:0.8rem;color:#4fc3f7;'>{ev.get('event_type','—')}</span>"
                f"<span style='font-size:0.75rem;color:#546e7a;'>{ev.get('source','—')}</span>"
                f"<span style='font-size:0.72rem;color:#37474f;'>{ev.get('timestamp','—')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
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
    q_data = [
        ("Completeness", quality.get("completeness")),
        ("Freshness", quality.get("freshness")),
        ("Consistency", quality.get("consistency")),
    ]
    for col, (label, val) in zip(q_cols, q_data):
        display = f"{val}%" if val is not None else "—"
        sub = f"{val}% average" if val is not None else "No data yet"
        col.markdown(
            f"<div class='nasmi-card' style='text-align:center;'>"
            f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
            f"letter-spacing:1px;'>{label}</div>"
            f"<div style='font-size:1.6rem;font-weight:700;color:#4fc3f7;margin-top:0.4rem;'>{display}</div>"
            f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>{sub}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

with col_side:

    # ── System Health ──
    st.markdown("#### 🟢 System Health")
    ollama_ok = _check_ollama()
    try:
        with Database() as db:
            db.fetchone("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    for service, ok in [
        ("Database", db_ok),
        ("OCR Engine", False),
        ("Ollama LLM", ollama_ok),
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
    alerts = []
    if stats["review_pending"]:
        alerts.append(f"✋ {stats['review_pending']} items pending review")
    if stats["contradictions"]:
        alerts.append(f"⚠️ {stats['contradictions']} unresolved contradictions")

    if alerts:
        for alert in alerts:
            st.markdown(
                f"<div class='nasmi-card' style='color:#ffcc80;font-size:0.82rem;"
                f"padding:0.6rem 1rem;border-left:3px solid #ffcc80;'>{alert}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div class='nasmi-card' style='color:#37474f;text-align:center;"
            "font-size:0.8rem;padding:1rem;'>"
            "No alerts at this time."
            "</div>",
            unsafe_allow_html=True,
        )
