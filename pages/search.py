import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "🔍",
    "Search & Query",
    "Search across documents · entities · knowledge — powered by NER + LLM",
)

# ── Session State ─────────────────────────────────────
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "search_mode" not in st.session_state:
    st.session_state.search_mode = "Smart Search"

# ── Search Bar ────────────────────────────────────────
col_input, col_mode, col_btn = st.columns([4, 2, 1])

with col_input:
    query = st.text_input(
        "Search",
        placeholder='e.g. "What is my IBAN?" · "Show all expired documents" · "Find address"',
        label_visibility="collapsed",
        value=st.session_state.search_query,
    )

with col_mode:
    mode = st.selectbox(
        "Mode",
        ["Smart Search", "Exact Match", "Semantic (LLM)", "Entity Lookup"],
        label_visibility="collapsed",
    )

with col_btn:
    search_btn = st.button("🔍 Search", use_container_width=True)

# ── Mode Description ──
mode_map = {
    "Smart Search": ("new", "Combines keyword + entity + semantic search"),
    "Exact Match": ("active", "Searches for exact text across all documents"),
    "Semantic (LLM)": (
        "pending",
        "Uses Ollama LLM to understand intent — slower but smarter",
    ),
    "Entity Lookup": ("new", "Searches by entity type: PERSON · DATE · ADDRESS · ID"),
}
m_status, m_desc = mode_map[mode]
st.markdown(
    f"<div style='margin-bottom:0.8rem;display:flex;align-items:center;gap:0.6rem;'>"
    f"{badge(mode, m_status)}"
    f"<span style='font-size:0.78rem;color:#546e7a;'>{m_desc}</span>"
    f"</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Filters Row ───────────────────────────────────────
with st.expander("🎛️ Advanced Filters", expanded=False):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        st.selectbox(
            "Entity Type", ["All", "PERSON", "DATE", "ADDRESS", "ID", "FINANCE", "GPE"]
        )
    with fc2:
        st.selectbox(
            "Document Type",
            ["All", "Personalausweis", "Reisepass", "Lohnabrechnung", "Other"],
        )
    with fc3:
        st.selectbox("Status", ["All", "Active", "Expired", "Pending", "Conflict"])
    with fc4:
        st.selectbox(
            "Sort By", ["Relevance", "Date Added", "Confidence", "Document Type"]
        )

# ── Results Area ──────────────────────────────────────
if search_btn and query.strip():
    st.session_state.search_query = query

    st.markdown(
        f"<div style='font-size:0.8rem;color:#546e7a;margin-bottom:0.8rem;'>"
        f"Searching for: <span style='color:#4fc3f7;font-weight:600;'>'{query}'</span> "
        f"using <span style='color:#4fc3f7;'>{mode}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Mock Results (replace with engine later) ──
    mock_results = [
        {
            "entity": "Full Name",
            "value": "—",
            "entity_type": "PERSON",
            "source_doc": "—",
            "doc_type": "Personalausweis",
            "confidence": 0,
            "status": "new",
            "date_added": "—",
        },
        {
            "entity": "IBAN",
            "value": "—",
            "entity_type": "FINANCE",
            "source_doc": "—",
            "doc_type": "Kontoauszug",
            "confidence": 0,
            "status": "new",
            "date_added": "—",
        },
        {
            "entity": "Address",
            "value": "—",
            "entity_type": "ADDRESS",
            "source_doc": "—",
            "doc_type": "Meldebescheinigung",
            "confidence": 0,
            "status": "pending",
            "date_added": "—",
        },
    ]

    st.markdown(f"#### 📋 Results ({len(mock_results)} found)")

    for r in mock_results:
        conf_color = (
            "#a5d6a7"
            if r["confidence"] >= 80
            else "#ffcc80" if r["confidence"] >= 50 else "#ef9a9a"
        )
        st.markdown(
            f"<div class='nasmi-card'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
            f"<div>"
            f"<div style='font-size:0.75rem;color:#546e7a;text-transform:uppercase;"
            f"letter-spacing:0.5px;'>{r['entity']}</div>"
            f"<div style='font-size:1.1rem;font-weight:600;color:#e3f2fd;margin-top:0.2rem;'>"
            f"{r['value']}</div>"
            f"<div style='font-size:0.75rem;color:#37474f;margin-top:0.3rem;'>"
            f"📄 {r['source_doc']} · {r['doc_type']} · Added: {r['date_added']}"
            f"</div>"
            f"</div>"
            f"<div style='display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem;'>"
            f"{badge(r['entity_type'], r['status'])}"
            f"<span style='font-size:0.72rem;color:{conf_color};'>"
            f"Confidence: {r['confidence']}%</span>"
            f"</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── LLM Answer Box (Semantic mode only) ──
    if mode == "Semantic (LLM)":
        st.markdown("#### 🤖 LLM Answer")
        st.markdown(
            "<div class='nasmi-card' style='border-left:3px solid #1565c0;"
            "padding:1rem 1.2rem;color:#546e7a;font-size:0.85rem;'>"
            "LLM engine (Ollama) is not connected yet. "
            "Semantic answers will appear here once the engine is active."
            "</div>",
            unsafe_allow_html=True,
        )

elif search_btn and not query.strip():
    st.warning("Please enter a search query.")

else:
    # ── Empty State ──
    st.markdown(
        "<div class='nasmi-card' style='text-align:center;padding:4rem 1rem;"
        "color:#37474f;border:2px dashed #1e2d4a;'>"
        "<div style='font-size:2.5rem;'>🔍</div>"
        "<div style='margin-top:0.5rem;font-size:0.9rem;'>Start searching your knowledge</div>"
        "<div style='font-size:0.75rem;margin-top:0.4rem;'>"
        "Try: 'What is my address?' · 'Show expired documents' · 'Find IBAN'"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Quick Searches ──
    st.markdown("#### ⚡ Quick Searches")
    qc1, qc2, qc3, qc4 = st.columns(4)
    qc1.button("🪪 My Identity Fields", use_container_width=True)
    qc2.button("📅 Expiring Documents", use_container_width=True)
    qc3.button("⚠️ Contradictions", use_container_width=True)
    qc4.button("💰 Financial Data", use_container_width=True)
